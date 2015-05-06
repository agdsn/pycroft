#!/usr/bin/env python2
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from __future__ import print_function

import os
import sys

from sqlalchemy import create_engine, distinct
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
                           finance, session, host, config, logging)
from pycroft.helpers import user as usertools

ROOT_NAME = "ag_dsn"
ROOT_PASSWD = "test"

def exists_db(connection, name):
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = {}".format(name)).first()
    connection.execute("COMMIT")

    return exists is not None


def translate(zimmer, wheim, nutzer, hp4108port, computer, subnet):
    records = []

    # TODO: missing or incomplete translations for finance, status/groups/permissions, patchport, traffic, incidents/log, vlans, dns, ...

    # order should match sorted_tables, but no individual translation functions
    # since appropriate mapping dicts [a-z]_d would need to be passed anyway

    print("Translating legacy data")
    b_d = {} # maps netusers.Wheim.id to translated sqlalchemy object
    print("  Translating buildings")
    for _b in wheim:
        b = facilities.Dormitory(
            id=_b.wheim_id,
            short_name=_b.kuerzel,
            street=_b.str,
            number=_b.hausnr)
        b_d[_b.wheim_id] = b
        records.append(b)

    print("  Translating rooms")
    r_d = {} # maps (wheim_id, etage, zimmernr) to translated sqlalchemy object
    for _r in zimmer:
        r = facilities.Room(dormitory=b_d[_r.wheim_id],
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
            finance_account=finance.FinanceAccount(name="", type="ASSET"))
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
            message="User imported from legacy DB",
            user=u))

    print("  Translating subnet")
    s_d = {} # you know the drill
    for _s in subnet:
        s = net.Subnet(address=_s.net_ip+"/"+_s.netmask,
                       gateway=_s.default_gateway,
                       dns_domain=_s.domain,
                       ip_type="4",
                       description=_s.vlan_name)
        s_d[_s.subnet_id] = s
        records.append(s)
    # TODO: note, missing transit, server and eduroam subnets

    print("  Translating computer")
    sw_d = {} # switch dict: mgmt_ip -> obj
    for _c in computer:
        owner = u_d[_c.nutzer_id]
        if _c.nutzer_id == 0:
            try:
                room = r_d[(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)]
            except KeyError:
                room = facilities.Room(dormitory=b_d[_c.c_wheim_id],
                                       level=_c.c_etage,
                                       number=_c.c_zimmernr or '?',
                                       inhabitable=False)

                r_d[(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)] = room
                records.append(room)

            if _c.c_typ == "Switch" or "switch" in _c.c_alias.lower():
                mgmt_ip_blocks = _c.c_ip.split(".")
                mgmt_ip_blocks[0] = mgmt_ip_blocks[1] = "10"
                mgmt_ip = ".".join(mgmt_ip_blocks)
                name = _c.c_alias or "unnamed_switch"
                h = host.Switch(owner=owner, name=name, management_ip=mgmt_ip, room=room)
                nd = host.SwitchNetDevice(host=h, mac=_c.c_etheraddr)
                ip = host.Ip(net_device=nd, address=_c.c_ip, subnet=s_d[_c.c_subnet_id])
                sw_d[mgmt_ip] = h
            else: #assume server
                h = host.ServerHost(owner=owner, name=_c.c_alias, room=room)
                nd = host.ServerNetDevice(host=h, mac=_c.c_etheraddr)
                ip = host.Ip(net_device=nd, address=_c.c_ip, subnet=s_d[_c.c_subnet_id])

        else: #assume user
            h = host.UserHost(owner=owner, room=owner.room)
            nd = host.UserNetDevice(host=h, mac=_c.c_etheraddr)

            ip = None
            if _c.nutzer.status == 1:
                ip = host.Ip(net_device=nd, address=_c.c_ip, subnet=s_d[_c.c_subnet_id])
        records.extend([h, nd])
        if ip:
            records.append(ip)

    print("  Translating hp4108ports")
    for _sp in hp4108port:
        try:
            switch = sw_d[_sp.ip]
            port_name = _sp.port
            sp = port.SwitchPort(switch=switch,name=port_name)
            # TODO insert proper patch_port names
            room = r_d[(_sp.wheim_id, int(_sp.etage), _sp.zimmernr)]
            pp = port.SwitchPatchPort(switch_port=sp, name="??", room=room)
            records.extend([sp, pp])
        except KeyError as e:
            # Bor34 switch isn't in computers
            print("KeyError: "+str(e))

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
    #                choices=cachable_tables)

    args = parser.parse_args()
    main(args)
