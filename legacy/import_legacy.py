#!/usr/bin/env pypy
# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import print_function

import os
import sys
import difflib
from datetime import datetime, timedelta, date
import logging as log

from tools import TranslationRegistry, timed

import sqlalchemy
from sqlalchemy import create_engine, or_, not_
import ipaddr
from sqlalchemy.sql import null
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import _request_ctx_stack

from conn import conn_opts
from import_conf import group_props, site_name_map, building_site_map
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

# TODO: missing or incomplete translations for status/groups/permissions, patchport, traffic, incidents/log, vlans, dns, ...

reg = TranslationRegistry()

@reg.provides(facilities.Site)
def generate_sites(data, resources):
    site_d = resources['site'] = {id_: facilities.Site(name=name)
                          for id_, name in site_name_map.items()}
    return site_d.values()


@reg.provides(facilities.Building)
def translate_buildings(data, resources):
    site_d = resources['site']

    b_d = resources['wheim'] = {}  # netusers.Wheim.id -> obj
    for _b in data['wheim']:
        b = facilities.Building(
            id=_b.wheim_id,
            site=site_d[building_site_map[_b.wheim_id]],
            short_name=_b.kuerzel,
            street=_b.str.replace(u'strasse', u'straße'),
            number=_b.hausnr)
        b_d[_b.wheim_id] = b
    return b_d.values()


@reg.provides(facilities.Room)
def translate_rooms(data, resources):
    b_d = resources['wheim']

    r_d = resources['zimmer'] = {}  # (wheim_id, etage, zimmernr) -> obj
    for _r in data['zimmer']:
        r = facilities.Room(
            building=b_d[_r.wheim_id],
            level=_r.etage,
            number=_r.zimmernr,
            inhabitable=True)

        # _r.etage is VARCHAR here,
        # conversion to int is needed since it's an int everywhere else
        r_d[(_r.wheim_id, int(_r.etage), _r.zimmernr)] = r
    return r_d.values()


@reg.provides(user.Property, user.PropertyGroup, user.Group)
def generate_groups(data, resources):
    properties_l = []
    g_d = resources['group'] = {}  # role -> PropertyGroup obj

    for role, (group_name, properties) in group_props.iteritems():
        g = user.PropertyGroup(name=group_name)
        g_d[role] = g
        for prop_name, modifier in properties.iteritems():
            properties_l.append(user.Property(
                name=prop_name, property_group=g, granted=modifier))
    return g_d.values()+properties_l


@reg.provides(logging.UserLogEntry)
def translate_logs(data, resources):
    # todo import userman.log
    # todo think of best way to import zih_incidents

    return []


@reg.satisfies(user.User.account_id)
@reg.provides(user.User, user.Membership)
def translate_users(data, resources):
    r_d = resources['zimmer']
    g_d = resources['group']

    objs = []
    u_d = resources['user'] = {}  # nutzer_id -> obj
    ul_d = resources['username'] = {}  # unix_account -> obj

    ignored_rooms = []
    for _u in data['nutzer']:
        login = _u.unix_account if _u.nutzer_id != 0 else ROOT_NAME
        try:
            room = r_d[(_u.wheim_id, _u.etage, _u.zimmernr)]
        except KeyError:
            ignored_rooms.append((_u.wheim_id, _u.etage, _u.zimmernr))
            room = None

        account_name = "Nutzerkonto von {}".format(_u.nutzer_id)
        u = user.User(
            id=_u.nutzer_id,
            login=login if not login[0].isdigit() else "user_"+login,
            name=_u.vname+" "+_u.name,
            email=login+"@wh2.tu-dresden.de", #TODO is this correct?
            room=room,
            registered_at=_u.anmeldedatum,
            account=finance.Account(name=account_name, type="USER_ASSET"))
        if _u.nutzer_id == 0:
            u.passwd_hash = usertools.hash_password(ROOT_PASSWD)
            objs.append(user.Membership(user=u, group=g_d["root"], begins_at=null()))
        elif _u.status_id in (1, 2, 4, 5, 7, 12):
            objs.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum))
        elif _u.status_id in (3, 6, 10):
            objs.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))
            objs.append(user.Membership(user=u, group=g_d["away"], begins_at=_u.last_change.date()))
        elif _u.status_id == 9: #ex-aktiv
            # since there are now time-based memberships, there is no need to have an ex-actives' group
            objs.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))
            objs.append(user.Membership(user=u, group=g_d["org"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))
        elif _u.status_id == 8: #ausgezogen
            objs.append(user.Membership(user=u, group=g_d["member"], begins_at=_u.anmeldedatum, ends_at=_u.last_change.date()))

        # suspended groups
        if _u.status_id in (5, 6, 7, 12):
            objs.append(user.Membership(user=u, group=g_d["suspended"], begins_at=_u.anmeldedatum))

        objs.append(u)
        u_d[_u.nutzer_id] = u
        ul_d[_u.unix_account] = u

        objs.append(logging.UserLogEntry(
            author=u_d.get(0, None),
            message="User imported from legacy database netusers. "
                    "Legacy status: "+_u.status.short_str,
            user=u))

        # user comment
        if _u.comment:
            objs.append(logging.UserLogEntry(
                author=u_d.get(0, None),
                message="Legacy comment: "+_u.comment,
                user=u))

    if ignored_rooms:
        log.warning("Ignoring {num} ({uniq}) rooms missing from hp4108port".format(
            num=len(ignored_rooms), uniq=len(set(ignored_rooms))))
    return objs


@reg.provides(finance.Semester)
def translate_semesters(data, resources):
    sem_d = {}

    gauge_stype, gauge_year, gauge_num = ("ws", 2014, 25) #id=25000 for WS14/15
    day={"ws": 1, "ss": 1}
    month={"ws": 10, "ss": 4}

    def semester_begin_date(i):
        stype = "ss" if (i%2==0) ^ (gauge_stype == "ws") else "ws"
        years_to_gauge = i//2 + (i%2 if stype != "ws" else 0)
        return date(day=day[stype],
                    month=month[stype],
                    year=gauge_year+years_to_gauge)

    for _sem in data['semester']:
        num_semesters_to_gauge = _sem.id/1000-gauge_num
        # fee changes:
        #   ws02/03 1000: anm2500 sem1750 red450
        #   ss04 4000: anm2500 sem1500 red450
        #   ws14/15 25000: anm0 sem2000 red100
        s = finance.Semester(
            name=_sem.name,
            registration_fee=25.00 if _sem.id < 25000 else 0.,
            regular_semester_fee=17.50 if _sem.id < 40.00 else (15.00 if _sem.id < 25000 else 20.00),
            reduced_semester_fee=4.50 if _sem.id < 25000 else 1.00,
            late_fee=2.50,
            grace_period=timedelta(days=62),
            reduced_semester_fee_threshold=timedelta(days=62),
            payment_deadline=timedelta(days=31),
            allowed_overdraft=5.00,
            begins_on=semester_begin_date(num_semesters_to_gauge),
            ends_on=semester_begin_date(num_semesters_to_gauge+1)-timedelta(days=1))
        sem_d[_sem.id] = s
    return sem_d.values()


@reg.provides(finance.Account)
def translate_finance_accounts(data, resources):
    # TODO: look over this
    facc_types = {
        u"Startguthaben": "REVENUE",
        u"Bankkonto": "BANK_ASSET",
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

    objs = []
    a_d = resources['account'] = {}
    an_d = resources['accountname'] = {}
    for name, type in facc_types.items():
        a = finance.Account(name=name, type=type)
        objs.append(a)
        an_d[name] = a

    # TODO: Think about this, this is a pretty unstable/volatile way to do things,
    #  maybe just save the generated dict to a file to allow for manual changes and
    #  oversight
    for _a in data['finanz_konten']:
        acc_name = (difflib.get_close_matches(_a.name,
                                          facc_types.keys(),
                                          n=1,
                                          cutoff=0.5) or [None])[0]
        log.debug(u"   {} {} -> {}".format(_a.id, _a.name, acc_name))

        if acc_name:
            a_d[_a.id] = an_d[acc_name]

        # make sure all accounts that are mapped to None do not have any
        # transactions associated with them

        assert not (acc_name is None and
                    (_a.haben_fb or _a.soll_fb or _a.bankbuchungen))

    return objs


@reg.provides(finance.BankAccount)
def generate_bank_account(data, resources):
    an_d = resources['accountname']

    bank_account = finance.BankAccount(
        name="Bankkonto 3120219540",
        bank="Ostsächsische Sparkasse Dresden",
        account_number="3120219540",
        routing_number="85050300",
        iban="DE61850503003120219540",
        bic="OSDDDE81XXX",
        hbci_url="https://hbci.example.com/",
        account=an_d["Bankkonto"])

    resources['bank_account'] = bank_account
    return [bank_account]


def simple_transaction(amount, credit_account, debit_account, description,
                       valid_on, author, **tx_kwargs):
    transaction = finance.Transaction(
        description=description or "NO DESCRIPTION GIVEN",
        author=author,
        valid_on=valid_on,
        **tx_kwargs)
    credit_split = finance.Split(
        amount=amount,
        account=credit_account,
        transaction=transaction)
    debit_split = finance.Split(
        amount=-amount,
        account=debit_account,
        transaction=transaction)

    return transaction, credit_split, debit_split


# chooses the new account id given an old account id and user id
def get_acc(old_account_id, old_user_id, u_d, a_d):
    if old_user_id: # user referenced
        if old_user_id not in u_d: # but doesn't exist
            account_name = ("Nutzerkonto von gelöschtem Nutzer {}"
                            .format(old_user_id))
            u = user.User(
                id=old_user_id,
                login="deleted_user_"+str(old_user_id),
                name="Gelöschter Nutzer "+str(old_user_id),
                registered_at=datetime.fromtimestamp(0),
                account=finance.Account(name=account_name, type="ASSET"))

            u_d[old_user_id] = u

        account = u_d[old_user_id].account
    else:
        account = a_d[old_account_id]

    return account


@reg.satisfies(finance.BankAccountActivity.transaction_id)
@reg.provides(finance.BankAccountActivity)
def translate_bank_transactions(data, resources):
    bank_account = resources['bank_account']

    bt_d = resources['bank_transaction'] = {}
    for _bt in data['bank_transaction']:
        bt = finance.BankAccountActivity(
            id=_bt.bkid,
            bank_account=bank_account,
            amount=_bt.wert,
            reference=_bt.bes,
            original_reference=_bt.bes,
            other_account_number="NO NUMBER GIVEN", #TODO fill these properly, somehow
            other_routing_number="NO NUMBER GIVEN", #TODO
            other_name="NO NAME GIVEN", #TODO
            import_time=_bt.valid_on,
            posted_at=_bt.valid_on,
            valid_on=_bt.valid_on,
            transaction=None)
        bt_d[_bt.bkid] = bt
    return bt_d.values()


@reg.requires_function(translate_bank_transactions)
@reg.provides(finance.Transaction, finance.Split)
def translate_finance_transactions(data, resources):
    a_d = resources['account']
    an_d = resources['accountname']
    u_d = resources['user']
    ul_d = resources['username']
    bt_d = resources['bank_transaction']

    objs = []

    #  § 199 Abs. 1 BGB
    # TODO write-offs? write off mail memberships, but not full fees
    # TODO reconstruct past memberships based on fees incurred
    # TODO inspect 4000 transaction on 10538

    for _bu in data['finance_transaction']:
        if _bu.wert == 0 and _bu.haben == _bu.soll:
            log.warning('Ignoring invalid zero-value transaction')
            continue

        tss = simple_transaction(
            id=_bu.fbid,
            author=ul_d.get(_bu.bearbeiter, u_d[0]),
            description=_bu.bes, valid_on=_bu.datum,
            posted_at=_bu.datum,
            credit_account=get_acc(_bu.haben, _bu.haben_uid, u_d, a_d),
            debit_account=get_acc(_bu.soll, _bu.soll_uid, u_d, a_d),
            amount=_bu.wert)

        objs.extend(tss)

    min_id = max(b.fbid for b in data['finance_transaction']) + 1
    for i, _bt in enumerate(data['accounted_bank_transaction']):
        tss = simple_transaction(
            id=min_id+i,
            amount=_bt.wert,
            credit_account=an_d[u"Bankkonto"],
            debit_account=get_acc(_bt.konto_id, _bt.uid, u_d, a_d),
            description=_bt.bes or "NO DESCRIPTION GIVEN",
            author=ul_d.get(_bt.bearbeiter, u_d[0]),
            valid_on=_bt.valid_on,
            posted_at=_bt.posted_at)

        bt_d[_bt.bkid].transaction = tss[0]
        objs.extend(tss)

    return objs


@reg.satisfies(dns.SOARecord.name_id, dns.SOARecord.mname_id)
@reg.provides(dns.DNSZone, dns.SOARecord)
def generate_dns_zone(data, resources):
    primary_host_zone = dns.DNSZone(name="agdsn.tu-dresden.de")
    urz_zone = dns.DNSZone(name="urz.tu-dresden.de")
    soa_record = dns.SOARecord(
        name=dns.DNSName(name="@", zone=primary_host_zone),
        mname=dns.DNSName(name="rnadm", zone=urz_zone),
        rname="wuensch.urz.tu-dresden.de.",
        serial=2010010800,
        refresh=10800,
        retry=3600,
        expire=3600000,
        minimum=86400)
    resources['primary_host_zone'] = primary_host_zone
    resources['soa_record'] = soa_record
    return primary_host_zone, soa_record


@reg.provides(net.VLAN, net.Subnet)
def generate_subnets_vlans(data, resources):
    primary_host_zone = resources['primary_host_zone']
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
        'UNEP': 348,
    }

    s_d = resources['subnet'] = {}
    for _s in data['subnet']:
        address = ipaddr.IPv4Network(_s.net_ip + "/" + _s.netmask)
        vlan = net.VLAN(name=_s.vlan_name,
                        vid=vlan_name_vid_map[_s.vlan_name])
        s = net.Subnet(address=address,
                       gateway=ipaddr.IPv4Address(_s.default_gateway),
                       primary_dns_zone=primary_host_zone,
                       reverse_dns_zone=primary_host_zone, # TODO temporary fix
                       description=_s.vlan_name,
                       vlan=vlan)
        s_d[_s.subnet_id] = s

    # TODO: note, missing transit, server and eduroam subnets

    return s_d.values()


@reg.satisfies(host.IP.interface_id, dns.AddressRecord.name_id)
@reg.provides(host.Host, host.Interface,
                host.ServerHost, host.UserHost, host.Switch,
                host.ServerInterface, host.UserInterface, host.SwitchInterface,
                host.IP, dns.AddressRecord)
def translate_hosts(data, resources):
    legacy_hostname_map = {}
    u_d = resources['user']
    s_d = resources['subnet']
    r_d = resources['zimmer']
    b_d = resources['wheim']
    primary_host_zone = resources['primary_host_zone']

    objs = []
    sw_d = resources['switch'] = {}  # switch dict: mgmt_ip -> obj

    def get_or_create_room(wheim_id, etage, zimmernr):
        try:
            room = r_d[(wheim_id, etage, zimmernr)]
        except KeyError:
            room = facilities.Room(building=b_d[wheim_id],
                                   level=etage,
                                   number=zimmernr or '?',
                                   inhabitable=False)

            r_d[(wheim_id, etage, zimmernr)] = room

        return room

    for _c in data['switch']:
        room = get_or_create_room(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)
        mgmt_ip_blocks = _c.c_ip.split(".")
        mgmt_ip_blocks[0] = mgmt_ip_blocks[1] = "10"
        mgmt_ip = ipaddr.IPv4Address(".".join(mgmt_ip_blocks))
        h = host.Switch(owner=u_d[0], name=_c.c_hname, management_ip=mgmt_ip, room=room)
        interface = host.SwitchInterface(host=h, mac=_c.c_etheraddr or "00:00:00:00:00:01", name="switch management interface")
        ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
        sw_d[mgmt_ip] = h
        objs.append(ip)

    for _c in data['server']:
        room = get_or_create_room(_c.c_wheim_id, _c.c_etage, _c.c_zimmernr)
        h = host.ServerHost(owner=u_d[0], name=_c.c_alias, room=room)
        interface = host.ServerInterface(host=h, mac=_c.c_etheraddr)
        ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
        hostname = legacy_hostname_map.get(_c.c_hname) or _c.c_hname
        if hostname and hostname != 'NULL':
            objs.append(dns.AddressRecord(name=dns.DNSName(name=hostname, zone=primary_host_zone), address=ip))
        else:
            objs.append(ip)

    for _c in data['userhost']:
        owner = u_d[_c.nutzer_id]
        h = host.UserHost(owner=owner, room=owner.room)
        interface = host.UserInterface(host=h, mac=_c.c_etheraddr)

        if _c.nutzer.status_id in (1, 2, 4, 5, 7, 12):
            hostname = generate_hostname(ipaddr.IPAddress(_c.c_ip))
            ip = host.IP(interface=interface, address=ipaddr.IPv4Address(_c.c_ip), subnet=s_d[_c.c_subnet_id])
            objs.append(dns.AddressRecord(name=dns.DNSName(name=hostname, zone=primary_host_zone), address=ip))
        else:
            objs.append(interface)
    return objs


@reg.provides(port.SwitchPatchPort)
def translate_ports(data, resources):
    sw_d = resources['switch']
    s_d = resources['subnet']
    r_d = resources['zimmer']

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

    objs = []
    for _sp in data['port']:
        mgmt_ip = ipaddr.IPv4Address(_sp.ip)
        try:
            switch = sw_d[mgmt_ip]
        except KeyError as e:
            log.warning("Ignoring hp4108port {}/{} due to missing switch in "
                           "legacy db".format(mgmt_ip, _sp.port))
            continue

        port_name = _sp.port
        room = r_d[(_sp.wheim_id, int(_sp.etage), _sp.zimmernr)]
        subnet_id = building_subnet_map[room.building.id]
        sp = host.SwitchInterface(
            host=switch, name=port_name,
            mac="00:00:00:00:00:01",
            default_subnet=s_d[subnet_id])
        # TODO insert proper patch_port names
        pp = port.SwitchPatchPort(
            switch_interface=sp, name="?? ({})".format(port_name), room=room)
        objs.append(pp)

    return objs


@reg.provides(config.Config)
def generate_config(data, resources):
    g_d = resources['group']
    an_d = resources['accountname']
    primary_host_zone = resources['primary_host_zone']

    return [config.Config(
        member_group=g_d["member"],
        violation_group=g_d["suspended"],
        network_access_group=g_d["member"],  # todo: actual network_access_group
        away_group=g_d["away"],
        moved_from_division_group=g_d["moved_from_division"],
        already_paid_semester_fee_group=g_d["already_paid"],
        registration_fee_account=an_d[u"Beiträge"],
        semester_fee_account=an_d[u"Beiträge"],
        late_fee_account=an_d[u"Beiträge"],
        additional_fee_account=an_d[u"Beiträge"],
        user_zone=primary_host_zone
)]


def translate(data):
    objs = []
    resources = {}

    log.info("Generating execution order...")
    for func in reg.sorted_functions():
        log.info("  {func}...".format(func=func.__name__))
        o = func(data, resources)
        log.info("  ...{func} ({num} objects).".format(
            func=func.__name__, num=len(o)))
        objs.extend(o)

    return objs

def main(args):
    engine = create_engine(os.environ['PYCROFT_DB_URI'], echo=False)
    session.set_scoped_session(
        scoped_session(sessionmaker(bind=engine),
                       scopefunc=lambda: _request_ctx_stack.top))

    if args.from_origin:
        log.info("Getting legacy data from origin")
        connection_string_nu = conn_opts["netusers"]
        connection_string_um = conn_opts["userman"]
    else:
        log.info("Getting legacy data from cache")
        connection_string_nu = connection_string_um = conn_opts["legacy"]

    engine_nu = create_engine(connection_string_nu, echo=False)
    session_nu = scoped_session(sessionmaker(bind=engine_nu))

    engine_um = create_engine(connection_string_um, echo=False)
    session_um = scoped_session(sessionmaker(bind=engine_um))

    master_engine = create_engine(conn_opts['master'])
    master_connection = master_engine.connect()
    master_connection.execute("COMMIT")

    log.info("Dropping pycroft db")
    master_connection.execute("DROP DATABASE IF EXISTS pycroft")
    master_connection.execute("COMMIT")
    log.info("Creating pycroft db")
    master_connection.execute("CREATE DATABASE pycroft")
    master_connection.execute("COMMIT")
    log.info("Creating pycroft model schema")
    model.create_db_model(engine)

    with timed(log, thing="Translation"):
        root_computer_cond = or_(netusers_model.Computer.nutzer_id == 0,
                                 netusers_model.Computer.nutzer_id == 11551)

        legacy_data = {
            'wheim': session_nu.query(netusers_model.Wheim).all(),
            'zimmer': session_nu.query(
                netusers_model.Hp4108Port.wheim_id,
                netusers_model.Hp4108Port.etage,
                netusers_model.Hp4108Port.zimmernr).distinct().all(),
            'nutzer': session_nu.query(netusers_model.Nutzer).all(),
            'semester': session_um.query(userman_model.FinanzKonten).filter(
                userman_model.FinanzKonten.id % 1000 == 0).all(),
            'finanz_konten': session_um.query(userman_model.FinanzKonten).filter(
                userman_model.FinanzKonten.id % 1000 != 0).all(),
            'switch': session_nu.query(netusers_model.Computer).filter(
                netusers_model.Computer.c_typ == 'Switch').all(),
            'server': session_nu.query(netusers_model.Computer)\
                .filter(netusers_model.Computer.c_typ != 'Switch')\
                .filter(netusers_model.Computer.c_typ != 'Router')\
                .filter(root_computer_cond).all(),
            'userhost': session_nu.query(netusers_model.Computer)\
                .filter(not_(root_computer_cond)).all(),
            'bank_transaction': session_um.query(userman_model.BankKonto).all(),
            'accounted_bank_transaction': session_um.query(
                userman_model.BkBuchung).all(),
            'finance_transaction': session_um.query(
                userman_model.FinanzBuchungen).all(),
            'subnet': session_nu.query(netusers_model.Subnet).all(),
            'port': session_nu.query(netusers_model.Hp4108Port).all(),
        }

        objs = translate(legacy_data)

    with timed(log, thing="Importing {} records".format(len(objs))):
        if args.bulk and map(int, sqlalchemy.__version__.split(".")) >= [1,0,0]:
            session.session.bulk_save_objects(objs)
        else:
            session.session.add_all(objs)
        session.session.commit()

    log.info("Fixing sequences...")
    for meta in (user.User, facilities.Building, finance.Transaction,
                 finance.BankAccountActivity):
        maxid = engine.execute('select max(id) from \"{}\";'.format(
            meta.__tablename__)).fetchone()[0]

        if maxid:
            engine.execute("select setval('{}_id_seq', {})".format(
                meta.__tablename__, maxid + 1))
            log.info("  fixing {}".format(meta.__tablename__))

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(prog='import_legacy',
                                     description='fill the hovercraft with eels')
    parser.add_argument("-l", "--log", dest="log_level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO')


    source = parser.add_mutually_exclusive_group()
    source.add_argument("--from-cache", action='store_true')
    source.add_argument("--from-origin", action='store_true')

    parser.add_argument("--bulk", action='store_true', default=False)
    parser.add_argument("--anonymize", action='store_true', default=False)
    parser.add_argument("--dump", action='store_true', default=False)
    #parser.add_argument("--tables", metavar="T", action='store', nargs="+",
    #                choices=cacheable_tables)

    args = parser.parse_args()
    if args.log_level:
        log.basicConfig(level=getattr(log, args.log_level))
    main(args)
    log.info("Import finished.")
