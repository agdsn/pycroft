#!/usr/bin/env python2
# coding=utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import print_function

import os
import sys
from datetime import datetime, timedelta

from sqlalchemy import create_engine, distinct
import ipaddr
from sqlalchemy.sql import null
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import _request_ctx_stack

from conn import conn_opts
from import_conf import group_props
import userman_model
import netusers_model
from userman import relevant_tables as tables_um
from netusers import relevant_tables as tables_nu

os.environ['PYCROFT_DB_URI'] = conn_opts['pycroft']

#so pycroft imports work, but as Raymond Hettinger would say:
#  "There must be a better way!"
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pycroft import model, property
from pycroft.model import (accounting, facilities, dns, user, net, port,
                           finance, session, host, config, logging, types)
from pycroft.lib.host import generate_hostname
from pycroft.helpers import user as usertools

ROOT_NAME = "agdsn"
ROOT_PASSWD = "test"

def exists_db(connection, name):
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = {}".format(name)).first()
    connection.execute("COMMIT")

    return exists is not None


def translate(zimmer, wheim, nutzer, finanz_konten, hp4108port, computer, subnet):
    records = []

    # TODO: missing or incomplete translations for finance, status/groups/permissions, patchport, traffic, incidents/log, vlans, dns, ...

    # order should match sorted_tables, but no individual translation functions
    # since appropriate mapping dicts [a-z]_d would need to be passed anyway

    print("Adding site")
    site = facilities.Site(name=u"Wundtstraße/Zellescher Weg")
    records.append(site)

    print("Translating legacy data")
    b_d = {} # maps netusers.Wheim.id to translated sqlalchemy object
    print("  Translating buildings")
    for _b in wheim:
        b = facilities.Building(
            id=_b.wheim_id,
            site=site,
            short_name=_b.kuerzel,
            street=_b.str,
            number=_b.hausnr)
        b_d[_b.wheim_id] = b
        records.append(b)

    print("  Translating rooms")
    r_d = {} # maps (wheim_id, etage, zimmernr) to translated sqlalchemy object
    for _r in zimmer:
        r = facilities.Room(building=b_d[_r.wheim_id],
                            level=_r.etage,
                            number=_r.zimmernr,
                            inhabitable=True)

        # _r.etage is VARCHAR, so conversion to int is needed, since it's an int everywhere else
        r_d[(_r.wheim_id, int(_r.etage), _r.zimmernr)] = r
        records.append(r)

    print("  Generating groups from import_conf")
    g_d = {}
    for role, (group_name, properties) in group_props.iteritems():
        g = user.PropertyGroup(name=group_name)
        g_d[role] = g
        records.append(g)
        for prop_name, modifier in properties.iteritems():
            records.append(
                user.Property(name=prop_name, property_group=g, granted=modifier))


    # no config entry is nullable, so TODO fill this when all finance accounts and groups are set up
    #config.Config(member_group=members,
    #              violation_group=violators
    #              )

    print("  Translating users")
    u_d = {} # maps (nutzer_id) to translated sqlalchemy object
    for _u in nutzer:
        login = _u.unix_account if _u.nutzer_id != 0 else ROOT_NAME
        room = r_d.get((_u.wheim_id, _u.etage, _u.zimmernr), None)
        u = user.User(
            id=_u.nutzer_id,
            login=login,
            name=_u.vname+" "+_u.name,
            email=login+"@wh2.tu-dresden.de", #TODO is this correct?
            room=room,
            registered_at=_u.anmeldedatum,
            finance_account=finance.FinanceAccount(name="Nutzerkonto "+login, type="ASSET"))
        if _u.nutzer_id == 0:
            u.passwd_hash = usertools.hash_password(ROOT_PASSWD)
            records.append(user.Membership(user=u, group=g_d["root"], begins_at=null()))
        elif _u.status == 1:
            records.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum))
        elif _u.status == 8:
            records.append(user.Membership(user=u, group=g_d["moved_out"], begins_at=null()))
        u_d[_u.nutzer_id] = u
        records.append(u)

        records.append(logging.UserLogEntry(
            author=u_d.get(0, None),
            message="User imported from legacy database netusers.",
            user=u))

    print("  Translating finance accounts")
    for _a in finanz_konten:
        if _a.id%1000 == 0:
            # fee changes:
            #   ws02/03 1000: anm2500 sem1750 red450
            #   ss04 4000: anm2500 sem1500 red450
            #   ws14/15 25000: anm0 sem2000 red100
            gauge_semester = datetime(year=2015, month=04, day=13) #26000
            semester_duration = timedelta(weeks=26)
            num_semesters_to_gauge = _a.id/1000-26
            s = finance.Semester(name=_a.name,
                                 registration_fee=2500 if _a.id < 25000 else 0,
                                 regular_semester_fee=1750 if _a.id < 4000 else (1500 if _a.id < 25000 else 2000),
                                 reduced_semester_fee=450 if _a.id < 25000 else 100,
                                 late_fee=250,
                                 grace_period=timedelta(days=62),
                                 reduced_semester_fee_threshold=timedelta(days=62),
                                 payment_deadline=timedelta(days=31),
                                 allowed_overdraft=500,
                                 begins_on=gauge_semester+num_semesters_to_gauge*semester_duration,
                                 ends_on=gauge_semester+(num_semesters_to_gauge+1)*semester_duration)
            records.append(s)


    print("  Adding DNS zones")
    primary_host_zone = dns.DNSZone(name="agdsn.tu-dresden.de")
    urz_zone = dns.DNSZone(name="urz.tu-dresden.de")
    records.append(dns.SOARecord(name=dns.DNSName(name="@", zone=primary_host_zone),
                                 mname=dns.DNSName(name="rnadm", zone=urz_zone),
                                 rname="wuensch.urz.tu-dresden.de.",
                                 serial=2010010800,
                                 refresh=10800,
                                 retry=3600,
                                 expire=3600000,
                                 minimum=86400))
    records.append(primary_host_zone)



    vlan_name_vid_map = {
        'Wu1': 11,
        'Wu3': 13,
        'Wu5': 15,
        'Wu7': 17,
        'Wu9': 19,
        'Wu11': 5,
        'ZW41': 41,
        'Bor34': 34,
        'Servernetz': 22,
        'UNEPWeb': 348,
    }

    print("  Translating subnet")
    s_d = {} # you know the drill
    for _s in subnet:
        address = ipaddr.IPv4Network(_s.net_ip + "/" + _s.netmask)
        vlan = net.VLAN(name=_s.vlan_name,
                        vid=vlan_name_vid_map[_s.vlan_name])
        s = net.Subnet(address=address,
                       gateway=ipaddr.IPv4Address(_s.default_gateway),
                       primary_dns_zone=primary_host_zone,
                       description=_s.vlan_name,
                       vlan=vlan)
        s_d[_s.subnet_id] = s
        records.append(s)
    # TODO: note, missing transit, server and eduroam subnets

    hname_hostname_map = {"test_alt": "test_neu"}

    print("  Translating computer")
    sw_d = {} # switch dict: mgmt_ip -> obj
    for _c in computer:
        owner = u_d[_c.nutzer_id]
        if _c.nutzer_id == 0:
            try:
                room = r_d[(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)]
            except KeyError:
                room = facilities.Room(building=b_d[_c.c_wheim_id],
                                       level=_c.c_etage,
                                       number=_c.c_zimmernr or '?',
                                       inhabitable=False)

                r_d[(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)] = room
                records.append(room)

            if _c.c_typ in ("Switch", "Router"):
                mgmt_ip_blocks = _c.c_ip.split(".")
                mgmt_ip_blocks[0] = mgmt_ip_blocks[1] = "10"
                mgmt_ip = ipaddr.IPv4Address(".".join(mgmt_ip_blocks))
                h = host.Switch(owner=owner, name=_c.c_hname, management_ip=mgmt_ip, room=room)
                interface = host.SwitchInterface(host=h, mac=_c.c_etheraddr, name="switch management interface")
                ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
                sw_d[mgmt_ip] = h
                records.append(ip)
            else: #assume server
                h = host.ServerHost(owner=owner, name=_c.c_alias, room=room)
                interface = host.ServerInterface(host=h, mac=_c.c_etheraddr)
                ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
                hostname = hname_hostname_map.get(_c.c_hname) or _c.c_hname
                if hostname and hostname != 'NULL':
                    records.append(dns.AddressRecord(name=dns.DNSName(name=hostname, zone=primary_host_zone), address=ip))
                else:
                    records.append(ip)
        else: #assume user
            h = host.UserHost(owner=owner, room=owner.room)
            interface = host.UserInterface(host=h, mac=_c.c_etheraddr)

            ip = None
            if _c.nutzer.status in (1, 2, 4, 5, 7, 12):
                hostname = generate_hostname(ipaddr.IPAddress(_c.c_ip))
                ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
                records.append(dns.AddressRecord(name=dns.DNSName(name=hostname, zone=primary_host_zone), address=ip))
        records.extend([h, interface])

    building_subnet_map = {
        1: 6,
        2: 3,
        3: 8,
        4: 7,
        5: 1,
        6: 2,
        7: 4,
        8: 4,
        9: 4,
        10: 4,
        11: 4,
        12: 10,
    }

    print("  Translating hp4108ports")
    for _sp in hp4108port:
        try:
            switch = sw_d[ipaddr.IPv4Address(_sp.ip)]
        except KeyError as e:
            # Bor34 switch isn't in computers
            print("KeyError: "+str(e))
            continue
        port_name = _sp.port
        room = r_d[(_sp.wheim_id, int(_sp.etage), _sp.zimmernr)]
        subnet_id = building_subnet_map[room.building.id]
        sp = host.SwitchInterface(host=switch, name=port_name,
                                  mac="00:00:00:00:00:01",
                                  default_subnet=s_d[subnet_id])
        # TODO insert proper patch_port names
        pp = port.SwitchPatchPort(switch_interface=sp, name="?? ({})".format(port_name), room=room)
        records.extend((sp, pp))

    return records

def main(args):
    engine = create_engine(os.environ['PYCROFT_DB_URI'], echo=False)
    session.set_scoped_session(
        scoped_session(sessionmaker(bind=engine),
                       scopefunc=lambda: _request_ctx_stack.top))

    if args.from_origin:
        print("Getting legacy data from origin")
        connection_string_nu = conn_opts["netusers"]
        connection_string_um = conn_opts["userman"]
    else:
        print("Getting legacy data from cache")
        connection_string_nu = connection_string_um = conn_opts["legacy"]

    engine_nu = create_engine(connection_string_nu, echo=False)
    session_nu = scoped_session(sessionmaker(bind=engine_nu))

    engine_um = create_engine(connection_string_um, echo=False)
    session_um = scoped_session(sessionmaker(bind=engine_um))

    master_engine = create_engine(conn_opts['master'])
    master_connection = master_engine.connect()
    master_connection.execute("COMMIT")

    print("Dropping pycroft db")
    master_connection.execute("DROP DATABASE IF EXISTS pycroft")
    master_connection.execute("COMMIT")
    print("Creating pycroft db")
    master_connection.execute("CREATE DATABASE pycroft")
    master_connection.execute("COMMIT")
    print("Creating pycroft model schema")
    model.create_db_model(engine)

    records = translate(wheim=session_nu.query(netusers_model.Wheim).all(),
                        zimmer=session_nu.query(netusers_model.Hp4108Port.wheim_id,
                                                netusers_model.Hp4108Port.etage,
                                                netusers_model.Hp4108Port.zimmernr).distinct().all(),
                        nutzer=session_nu.query(netusers_model.Nutzer).all(),
                        finanz_konten=session_um.query(userman_model.FinanzKonten).all(),
                        subnet=session_nu.query(netusers_model.Subnet).all(),
                        hp4108port=session_nu.query(netusers_model.Hp4108Port).all(),
                        computer=session_nu.query(netusers_model.Computer).all())

    print("Importing records ("+str(len(records))+")")
    session.session.add_all(records)
    session.session.commit()

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(prog='import_legacy',
                                     description='fill the hovercraft with eels')
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--from-cache", action='store_true')
    source.add_argument("--from-origin", action='store_true')

    #parser.add_argument("--tables", metavar="T", action='store', nargs="+",
    #                choices=cacheable_tables)

    args = parser.parse_args()
    main(args)
