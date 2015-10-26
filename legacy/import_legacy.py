#!/usr/bin/env pypy
# coding=utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import print_function

import os
import sys
import difflib
import time
from datetime import datetime, timedelta, date

from tools import memoized

import sqlalchemy
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


def translate(zimmer, wheim, nutzer, status, finanz_konten, bankkonto, buchungen, hp4108port, computer, subnet):
    records = []

    # TODO: missing or incomplete translations for finance, status/groups/permissions, patchport, traffic, incidents/log, vlans, dns, ...

    # order should match sorted_tables, but no individual translation functions
    # since appropriate mapping dicts [a-z]_d would need to be passed anyway

    print("Adding site")
    sites = [facilities.Site(name=u"Wundtstraße/Zellescher Weg"),
             facilities.Site(name=u"Borsbergstraße")]
    records.extend(sites)

    print("Translating legacy data")
    b_d = {} # maps netusers.Wheim.id to translated sqlalchemy object
    print("  Translating buildings")
    for _b in wheim:
        b = facilities.Building(
            id=_b.wheim_id,
            site=sites[0] if "Borsberg" not in _b.str else sites[1],
            short_name=_b.kuerzel,
            street=_b.str.replace(u'strasse', u'straße'),
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

    status_d = {}
    for s in status:
        status_d[s.id] = s.short_str

    print("  Translating users")
    u_d = {}  # maps nutzer_id to translated sqlalchemy object
    ul_d = {}  # maps unix_account to translated sqlalchemy object
    for _u in nutzer:
        login = _u.unix_account if _u.nutzer_id != 0 else ROOT_NAME
        room = r_d.get((_u.wheim_id, _u.etage, _u.zimmernr), None)
        u = user.User(
            id=_u.nutzer_id,
            login=login if not login[0].isdigit() else "user_"+login,
            name=_u.vname+" "+_u.name,
            email=login+"@wh2.tu-dresden.de", #TODO is this correct?
            room=room,
            registered_at=_u.anmeldedatum,
            finance_account=finance.FinanceAccount(name="Nutzerkonto von "+str(_u.nutzer_id), type="ASSET"))
        if _u.nutzer_id == 0:
            u.passwd_hash = usertools.hash_password(ROOT_PASSWD)
            records.append(user.Membership(user=u, group=g_d["root"], begins_at=null()))
        elif _u.status in (1, 2, 4, 5, 7, 12):
            records.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum))
        elif _u.status in (3, 6, 10):
            records.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))
            records.append(user.Membership(user=u, group=g_d["away"], begins_at=_u.last_change.date()))
        elif _u.status == 9: #ex-aktiv
            # since there are now time-based memberships, there is no need to have an ex-actives' group
            records.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))
            records.append(user.Membership(user=u, group=g_d["org"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))
        elif _u.status == 8: #ausgezogen
            records.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))

        # suspended groups
        if _u.status in (5, 6, 7, 12):
            records.append(user.Membership(user=u, group=g_d["suspended"], begins_at=_u.anmeldedatum))

        u_d[_u.nutzer_id] = u
        ul_d[_u.unix_account] = u
        records.append(u)

        records.append(logging.UserLogEntry(
            author=u_d.get(0, None),
            message="User imported from legacy database netusers. "
                    "Legacy status: "+status_d[_u.status],
            user=u))

        # user comment
        if _u.comment:
            records.append(logging.UserLogEntry(
                author=u_d.get(0, None),
                message="Legacy comment: "+_u.comment,
                user=u))

    # TODO: look over this
    facc_types = {u"Startguthaben": "REVENUE",
                  u"Bankkonto": "ASSET",
                  u"Bankgebühren": "EXPENSE",
                  u"Abgaben": "EXPENSE",  # Abgaben = ?
                  u"Sonstige Ausgaben": "EXPENSE",
                  u"Nutzerkonto": "ASSET",
                  u"Forderungen": "ASSET",
                  u"Verbindlichkeiten": "LIABILITY",  # offene Rechnungen
                  u"Beiträge": "REVENUE",
                  u"Spenden": "REVENUE",
                  u"Aktive Technik": "EXPENSE",
                  u"Passive Technik": "EXPENSE",
                  u"Büromaterial": "EXPENSE",
                  u"Öffentlichkeitsarbeit": "EXPENSE",
                  u"Beitragsabschreibung": "EXPENSE"}

    fk_d = {fk.id: fk.name for fk in finanz_konten}

    # TODO: Think about this, this is a pretty unstable/volatile way to do things,
    #  maybe just save the generated dict to a file to allow for manual changes and
    #  oversight
    @memoized
    def match(fk_id):
        return (difflib.get_close_matches(fk_d[fk_id],
                                          facc_types.keys(),
                                          n=1,
                                          cutoff=0.5) or [None])[0]

    print("  Creating finance accounts")
    sem_d = {}
    a_d = {}
    for name, type in facc_types.items():
        a = finance.FinanceAccount(name=name, type=type)
        records.append(a)
        a_d[name] = a

    print("  Adding bank journal")
    bank_journal = finance.Journal(name="Bankkonto 3120219540",
                                   bank="Ostsächsische Sparkasse Dresden",
                                   account_number="3120219540",
                                   routing_number="85050300",
                                   iban="DE61850503003120219540",
                                   bic="OSDDDE81XXX",
                                   hbci_url="https://hbci.example.com/",
                                   finance_account=a_d["Bankkonto"])
    records.append(bank_journal)

    print("  Translating finance accounts")
    gauge_stype, gauge_year, gauge_num = ("ws", 2014, 25) #id=25000 for WS14/15
    day={"ws": 1, "ss": 1}
    month={"ws": 10, "ss": 4}

    def semester_begin_date(i):
        stype = "ss" if (i%2==0) ^ (gauge_stype == "ws") else "ws"
        years_to_gauge = i//2 + (i%2 if stype != "ws" else 0)
        return date(day=day[stype],
                    month=month[stype],
                    year=gauge_year+years_to_gauge)

    for _a in finanz_konten:
        if _a.id%1000 == 0:
            num_semesters_to_gauge = _a.id/1000-gauge_num
            # fee changes:
            #   ws02/03 1000: anm2500 sem1750 red450
            #   ss04 4000: anm2500 sem1500 red450
            #   ws14/15 25000: anm0 sem2000 red100
            s = finance.Semester(name=_a.name,
                                 registration_fee=2500 if _a.id < 25000 else 0,
                                 regular_semester_fee=1750 if _a.id < 4000 else (1500 if _a.id < 25000 else 2000),
                                 reduced_semester_fee=450 if _a.id < 25000 else 100,
                                 late_fee=250,
                                 grace_period=timedelta(days=62),
                                 reduced_semester_fee_threshold=timedelta(days=62),
                                 payment_deadline=timedelta(days=31),
                                 allowed_overdraft=500,
                                 begins_on=semester_begin_date(num_semesters_to_gauge),
                                 ends_on=semester_begin_date(num_semesters_to_gauge+1)-timedelta(days=1))
            sem_d[_a.id] = s
            records.append(s)
        else:
            acc_name = match(_a.id)
            print("   ", _a.id, _a.name, "->", acc_name)

            # make sure we can translate all movements
            assert bool(acc_name) or not any((_a.haben_buchungen,_a.soll_buchungen))

    print("  Translating bank transactions")
    je_d = {}
    for _bk in bankkonto:
        je = finance.JournalEntry(
            journal=bank_journal,
            amount=_bk.wert,
            description=_bk.bes,
            original_description=_bk.bes,
            other_account_number="NO NUMBER GIVEN", #TODO fill these properly, somehow
            other_routing_number="NO NUMBER GIVEN", #TODO
            other_name="NO NAME GIVEN", #TODO
            import_time=_bk.datum,
            posted_at=_bk.datum,
            valid_on=_bk.datum,
            transaction=None)
        je_d[_bk.bkid] = je
        records.append(je)

    print("  Translating accounting transactions")

    # chooses the new account id given an old accounting transaction and user id
    def new_acc(old_account_id, old_user_id):
        if old_user_id: # user referenced
            if old_user_id not in u_d: # but doesn't exist
                u = user.User(
                    id=old_user_id,
                    login="deleted_user_"+str(old_user_id),
                    name="Gelöschter Nutzer "+str(old_user_id),
                    registered_at=datetime.fromtimestamp(0),
                    finance_account=finance.FinanceAccount(name="Nutzerkonto von gelöschtem Nutzer"+str(old_user_id), type="ASSET"))

                u_d[old_user_id] = u
                records.append(u)

            account = u_d[old_user_id].finance_account
        else:
            account = a_d[match(old_account_id)]

        return account

    #  § 199 Abs. 1 BGB
    # TODO write-offs? write off mail memberships, but not full fees
    # TODO reconstruct past memberships based on fees incurred
    # TODO inspect 4000 transaction on 10538

    for _bu in buchungen:
        if _bu.wert == 0 and _bu.haben == _bu.soll:
            continue # ignore
        if (_bu.haben is None and _bu.soll == 1) or (_bu.soll is None and _bu.haben == 1):
            continue # unaccounted banking expense, nothing to do
        if _bu.soll in match.cache and _bu.haben in match.cache:
            credit_account, debit_account = (new_acc(_bu.haben, _bu.haben_uid),
                                             new_acc(_bu.soll, _bu.soll_uid))

            transaction = finance.Transaction(
                id=_bu.oid,
                description=_bu.bes or "NO DESCRIPTION GIVEN",
                author=ul_d.get(_bu.bearbeiter, u_d[0]),
                valid_on=_bu.datum,
                posted_at=_bu.datum)
            new_credit_split = finance.Split(
                amount=_bu.wert,
                account=credit_account,
                transaction=transaction)
            new_debit_split = finance.Split(
                amount=-_bu.wert,
                account=debit_account,
                transaction=transaction)

            if _bu.bkid is not None: # link transaction with bank journal
                je_d[_bu.bkid].transaction = transaction
            records.extend([transaction, new_credit_split, new_debit_split])
        else:
            raise Exception("Unhandled accounting transaction")

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
        if _c.nutzer_id == 0 or _c.nutzer_id == 11551:  # 11551: bor34
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
                h = host.Switch(owner=u_d[0], name=_c.c_hname, management_ip=mgmt_ip, room=room)
                interface = host.SwitchInterface(host=h, mac=_c.c_etheraddr, name="switch management interface")
                ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
                sw_d[mgmt_ip] = h
                records.append(ip)
            else: #assume server
                h = host.ServerHost(owner=u_d[0], name=_c.c_alias, room=room)
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
        mgmt_ip = ipaddr.IPv4Address(_sp.ip)
        try:
            switch = sw_d[mgmt_ip]
        except KeyError as e:
            if _sp.haus == "Borsi34":
                # Bor34 switch isn't in computers, add it
                ip_blocks = _sp.ip.split(".")
                ip_blocks[0] = "141"
                ip_blocks[1] = "76"
                bor34_subnet_id = 10
                switch = host.Switch(owner=u_d[0], name="bor34switch", management_ip=mgmt_ip, room=None) #TODO room
                interface = host.SwitchInterface(host=switch, mac="00:00:00:00:00:01", name="switch management interface") #TODO proper mac addresses
                ip = host.IP(interface=interface, address=ipaddr.IPv4Address(".".join(ip_blocks)), subnet=s_d[bor34_subnet_id])
                records.extend([switch, interface, ip])
                sw_d[mgmt_ip] = switch
            else:
                raise
        port_name = _sp.port
        room = r_d[(_sp.wheim_id, int(_sp.etage), _sp.zimmernr)]
        subnet_id = building_subnet_map[room.building.id]
        sp = host.SwitchInterface(host=switch, name=port_name,
                                  mac="00:00:00:00:00:01",
                                  default_subnet=s_d[subnet_id])
        # TODO insert proper patch_port names
        pp = port.SwitchPatchPort(switch_interface=sp, name="?? ({})".format(port_name), room=room)
        records.extend((sp, pp))


    # no config entry is nullable, so TODO fill this when all finance accounts and groups are set up
    records.append(config.Config(member_group=g_d["member"],
                    violation_group=g_d["suspended"],
                    network_access_group=g_d["member"],  # todo: actual network_access_group
                    away_group=g_d["away"],
                    moved_from_division_group=g_d["moved_from_division"],
                    already_paid_semester_fee_group=g_d["already_paid"],
                    registration_fee_account=a_d[u"Beiträge"],
                    semester_fee_account=a_d[u"Beiträge"],
                    late_fee_account=a_d[u"Beiträge"],
                    additional_fee_account=a_d[u"Beiträge"],
                    user_zone=primary_host_zone
                  ))

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
                        status=session_nu.query(netusers_model.Status).all(),
                        finanz_konten=session_um.query(userman_model.FinanzKonten).all(),
                        bankkonto=session_um.query(userman_model.BankKonto).all(),
                        buchungen=session_um.query(userman_model.Buchungen).all(),
                        subnet=session_nu.query(netusers_model.Subnet).all(),
                        hp4108port=session_nu.query(netusers_model.Hp4108Port).all(),
                        computer=session_nu.query(netusers_model.Computer).all())

    print("Importing records ("+str(len(records))+")")
    t = time.time()
    if args.bulk and map(int, sqlalchemy.__version__.split(".")) >= [1,0,0]:
        session.session.bulk_save_objects(records)
    else:
        session.session.add_all(records)
    session.session.commit()
    print("...took",time.time()-t,"seconds.")

    print("Fixing sequences...")
    for table in (user.User, facilities.Building, finance.Transaction):
        maxid = engine.execute('select max(id) from \"{}\";'.format(table.__tablename__)).fetchone()[0]
        engine.execute("select setval('{}_id_seq', {})".format(table.__tablename__, maxid + 1))
    print("Done.")

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(prog='import_legacy',
                                     description='fill the hovercraft with eels')
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--from-cache", action='store_true')
    source.add_argument("--from-origin", action='store_true')

    parser.add_argument("--bulk", action='store_true', default=False)
    parser.add_argument("--anonymize", action='store_true', default=False)
    parser.add_argument("--dump", action='store_true', default=False)
    #parser.add_argument("--tables", metavar="T", action='store', nargs="+",
    #                choices=cacheable_tables)

    args = parser.parse_args()
    main(args)
