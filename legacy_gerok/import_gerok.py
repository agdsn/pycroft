#!/usr/bin/env pypy
# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import logging as std_logging
import os
import sys
from datetime import timedelta

import ipaddr

from legacy_gerok.nvtool_model import Location, Switch, Port, Subnet, Jack, \
    Account, Active

BANKKONTO_GER = "Bankkonto Ger"

log = std_logging.getLogger('import')

from .tools import timed

from sqlalchemy import create_engine, null
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import _request_ctx_stack

try:
    from .conn import conn_opts
except ImportError:
    print("Please provide configuration in the legacy_gerok/conn.py module.\n"
          "See conn.py.example for the required variables"
          " and further documentation.")
    exit()
os.environ['PYCROFT_DB_URI'] = conn_opts['pycroft']
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pycroft import model
from pycroft.model import (facilities, user, net, port, traffic,
                           finance, session, host, config, logging)
from pycroft.helpers import user as usertools

from legacy.import_conf import group_props

ROOT_NAME = "agdsn"
ROOT_PASSWD = "test"


def exists_db(connection, name):
    """Check whether a database exists.

    :param connection: A connection
    :param name: The name of the database
    :returns: Whether the db exists
    :rtype: bool
    """
    exists = connection.execute(
        "SELECT 1 FROM pg_database WHERE datname = {}".format(name)).first()
    connection.execute("COMMIT")

    return exists is not None


def main(args):
    """Import the legacy data according to ``args``"""
    engine = create_engine(os.environ['PYCROFT_DB_URI'], echo=False)
    session.set_scoped_session(
        scoped_session(sessionmaker(bind=engine),
                       scopefunc=lambda: _request_ctx_stack.top))

    connection_string_nvtool = conn_opts["nvtool"]

    engine_nvtool = create_engine(connection_string_nvtool, echo=False)
    session_nvtool = scoped_session(sessionmaker(bind=engine_nvtool))

    if args.delete_old:
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

    try:

        with timed(log, thing="Translation"):
            bank_account = create_bankAccount()
            building = create_site_and_building()
            ger38subnet, sn = create_subnet(session_nvtool)
            groups = get_or_create_groups()
            root_user = get_or_create_root_user(groups)
            import_facilities_and_switches(session_nvtool, building, ger38subnet,
                                           root_user)
            import_SwitchPatchPorts(session_nvtool, building, sn, ger38subnet)
            fee_account = get_or_create_config(groups)
            import_users(session_nvtool, building, groups, ger38subnet, fee_account,
                         bank_account, root_user)

        session.session.commit()
    except Exception as e:
        log.error(e)
        session.session.rollback()
    finally:
        session.session.close()

def create_bankAccount():

    existing_account = session.session.query(finance.BankAccount).filter(finance.BankAccount.account_number == "3120230811").scalar()

    if existing_account is not None:
        return existing_account

    bank_financeAccount = finance.Account(name=BANKKONTO_GER,
                                          type="BANK_ASSET")
    session.session.add(bank_financeAccount)
    bank_account = finance.BankAccount(
        name="Bankkonto 3120230811",
        bank="Ostsächsische Sparkasse Dresden",
        account_number="3120230811",
        routing_number="85050300",
        iban="DE33850503003120230811",
        bic="OSDDDE81XXX",
        account=bank_financeAccount)
    session.session.add(bank_account)
    log.info("Created Bank Account")
    return bank_account


def get_or_create_config(g_d):
    log.info("Get or create basic configuration")

    conf = session.session.query(config.Config).first()
    if conf is None:
        fee_account = finance.Account(name="Beiträge", type="REVENUE")
        session.session.add(fee_account)

        con = config.Config(
            member_group=g_d["member"],
            violation_group=g_d["suspended"],
            network_access_group=g_d["member"],
            # todo: actual network_access_group
            away_group=g_d["away"],
            moved_from_division_group=g_d["moved_from_division"],
            already_paid_semester_fee_group=g_d["already_paid"],
            registration_fee_account=fee_account,
            semester_fee_account=fee_account,
            late_fee_account=fee_account,
            additional_fee_account=fee_account,
        )

        session.session.add(con)
    else:
        fee_account = conf.semester_fee_account

    return fee_account


def import_SwitchPatchPorts(session_nvtool, building, sn, subnet):
    log.info("fill switches with ports and pull cabels through the house")

    # As on the last check (2017-09-03) there are no active cables to jacks with other numbers.
    # After cabeling to gigabit no userport was left and the stystemports are not in use.
    jacks = session_nvtool.query(Jack).filter(
        (Jack.number == 1) & (Jack.subnet == sn))
    for j in jacks:
        switch = session.session.query(host.Switch).filter(
            host.Switch.management_ip == j.port.switch.ip).one()

        port_name = str(j.port.number)
        sp = host.SwitchPort(switch= switch, name=port_name, default_vlans=[subnet.vlan])

        inhabitable, isswitchroom, room_number = get_room_properties(j.location)

        room = session.session.query(facilities.Room).filter(
            (facilities.Room.building == building) &
            (facilities.Room.level == j.location.floor.number) &
            (facilities.Room.number == room_number)).one()

        existing_ports = session.session.query(port.PatchPort).filter(port.PatchPort.room
                                                              == room).all()
        # already imported
        if existing_ports:
            log.info("Ports already existing")
            return

        pp = port.PatchPort(
            switch_port=sp,
            room=room,
            name="{flat}{room}".format(flat=j.location.flat,
                                       room=j.location.room, )
        )
        session.session.add(pp)


def create_site_and_building():

    existing_building = session.session.query(facilities.Building).filter(
        facilities.Building.short_name == "Ger38").scalar()
    if existing_building is not None:
        return existing_building

    traffic_group = session.session.query(user.TrafficGroup).first()

    site = facilities.Site(
        name="Gerokstraße"
    )
    building = facilities.Building(
        id=38,
        site=site,
        short_name="Ger38",
        street="Gerokstraße",
        number="38",
        default_traffic_group=traffic_group)

    log.info("Created Site and Building")
    return building


def create_subnet(session_nvtool):
    # Exclude Ger27
    sn = session_nvtool.query(Subnet).filter(Subnet.id != 1).one()

    ger38subnet = net.Subnet(
        address=ipaddr.IPNetwork(sn.network),
        gateway=ipaddr.IPAddress(sn.gateway),
        vlan=net.VLAN(
            name="Hausnetz Ger38",
            vid=38
        )
    )

    log.info("Created Subnet with Vlan")

    return ger38subnet, sn


def import_facilities_and_switches(session_nvtool, building, ger38subnet, root_user):
    log.info("Importing Rooms and Switches")

    oldRooms = session.session.query(facilities.Room).filter(facilities.Room.building == building).all()
    if oldRooms:
        log.info("Rooms already imported")
        return

    # Only Gerok 38 locations
    locations = session_nvtool.query(Location).filter(Location.domain_id == 2)
    for l in locations:
        inhabitable, isswitchroom, number = get_room_properties(l)

        room = facilities.Room(
            inhabitable=inhabitable,
            building=building,
            level=l.floor.number,
            number=number
        )
        building.rooms.append(room)

        if (isswitchroom):
            switches = session_nvtool.query(Switch).filter(Switch.location == l)
            for s in switches:
                h = host.Host(owner=root_user, room=room)
                switch = host.Switch(
                    name=s.comment,
                    management_ip=s.ip,
                    host=h
                )

                session.session.add(switch)

    session.session.add(building)
    session.session.commit()


def import_users(session_nvtool, building, groups, ger38subnet, fee_account,
                 bank_account, root_user):

    log.info("Import User")

    ger38locations = session_nvtool.query(Location.id).filter(
        Location.domain_id == 2)
    legacy_accounts = session_nvtool.query(Account).filter(
        Account.location_id.in_(ger38locations))

    importcount = 0
    for account in legacy_accounts:
        create_user_with_all_data(account, bank_account, building,
                                  fee_account, ger38subnet, groups, root_user,
                                  session_nvtool)
        importcount +=1

    log.info("Imported {} Users".format(importcount))


def create_user_with_all_data(account, bank_account, building, fee_account,
                              ger38subnet, groups, ru, session_nvtool):
    log.debug("Importing User {}".format(account.name))
    room = get_room_for_location(account, building)
    financeAccount = get_finance_account_for_user(account)
    u = create_user(account, financeAccount, room, ru)
    create_finance_transactions_for_user(account, bank_account, fee_account,
                                         financeAccount, ru)
    setup_groups_for_user(account, groups, session_nvtool, u)
    add_user_hosts(account, building, ger38subnet, room, u, groups)


def add_user_hosts(account, building, ger38subnet, room, u, groups):
    for legacy_host in account.hosts:
        mac = legacy_host.mac

        macs = session.session.query(host.Interface).filter(host.Interface.mac ==
                                                           mac.macaddr).all()

        if macs:
            log.warning("Ignoring host %s for user %s cause mac already exists",
                        mac.macaddr, u.name)
            return

        hostLocation = mac.jack.location
        inhabitable, isswitchroom, room_number = get_room_properties(hostLocation)
        hostroom = session.session.query(facilities.Room).filter(
            (facilities.Room.building == building) &
            (facilities.Room.level == hostLocation.floor.number) &
            (facilities.Room.number == room_number)).one()

        if room != hostroom and "Müllraum" in hostroom.number:
            continue
        else:
            h = host.Host(owner=u, room=room)
            interface = host.Interface(host=h, mac=mac.macaddr)

        address = ipaddr.IPv4Network(mac.ip.ip).ip
        ip = host.IP(interface=interface,
                     address=address,
                     subnet=ger38subnet)

        session.session.add(ip)
        now = session.utcnow()
        trafficlimit = groups["usertraffic"].credit_limit
        credit = traffic.TrafficCredit(user=u, timestamp=now,
                                               amount=trafficlimit)
        session.session.add(credit)


def setup_groups_for_user(account, groups, session_nvtool, u):
    if "Hausmeister" not in account.name:
        usergroupmember = user.Membership(user=u, group=groups["member"],
                                          begins_at=account.entrydate)
    else:
        usergroupmember = user.Membership(user=u, group=groups["caretaker"],
                                          begins_at=account.entrydate)
    session.session.add(usergroupmember)

    traffic = user.Membership(user=u, group=groups["usertraffic"],
                              begins_at=account.entrydate)
    session.session.add(traffic)

    active = session_nvtool.query(Active).filter(
        Active.account == account).one_or_none()
    if not active is None:
        if active.activegroup_id == 10:  # oldstaff
            oldstaff = user.Membership(user=u, group=groups["org"],
                                       begins_at=account.entrydate,
                                       ends_at=account.entrydate + timedelta(
                                           days=1))
            session.session.add(oldstaff)
        else:
            staff = user.Membership(user=u, group=groups["org"],
                                    begins_at=account.entrydate)
            session.session.add(staff)


def create_finance_transactions_for_user(account, bank_account, fee_account,
                                         finance_account, ru):
    for trans in account.financetransactions:
        # Mitgliedsbeitrag
        if trans.banktransfer is not None:
            create_bank_transfer_transaction(bank_account, finance_account, ru, trans)

        # Semesterbeitrag
        if trans.fee is not None:
            create_userfee_transaction(fee_account, finance_account, ru, trans)


def create_userfee_transaction(fee_account, finance_account, ru, trans):
    transaction = finance.Transaction(
        description=trans.fee.description,
        author=ru,
        valid_on=trans.fee.duedate,
        posted_at=trans.fee.duedate)
    credit_split = finance.Split(
        amount=trans.amount,
        account=fee_account,
        transaction=transaction,
    )
    debit_split = finance.Split(
        amount=-trans.amount,
        account=finance_account,
        transaction=transaction
    )
    session.session.add(transaction)
    session.session.add(credit_split)
    session.session.add(debit_split)


def create_bank_transfer_transaction(bank_account, finance_account, ru, trans):
    back_account_activity = finance.BankAccountActivity(
        bank_account=bank_account,
        amount=trans.banktransfer.amount,
        reference=trans.banktransfer.purpose,
        original_reference=trans.banktransfer.purpose,
        other_account_number=trans.banktransfer.iban,
        other_routing_number=trans.banktransfer.bic,
        other_name=trans.banktransfer.name,
        imported_at=trans.banktransfer.date,
        posted_on=trans.banktransfer.date,
        valid_on=trans.banktransfer.date,
        split=None)
    transaction = finance.Transaction(
        description=trans.banktransfer.purpose or "NO DESCRIPTION GIVEN",
        author=ru,
        valid_on=trans.banktransfer.date,
        posted_at=trans.banktransfer.date)
    credit_split = finance.Split(
        amount=trans.amount,
        account=bank_account.account,
        bank_account_activity=back_account_activity,
        transaction=transaction,
    )
    debit_split = finance.Split(
        amount=-trans.amount,
        account=finance_account,
        transaction=transaction
    )
    session.session.add(transaction)
    session.session.add(credit_split)
    session.session.add(debit_split)


def create_user(account, financeAccount, room, ru):
    login = account.login
    if not user.User.login_regex.match(account.login):
        login = "user_{}".format(account.id)
        log.warning("Rename login '%s' to '%s'", account.login, login)

    existing_user = session.session.query(user.User).filter(user.User.login == login).scalar()
    if (existing_user is not None):
        login = login + "_gerok"
        log.warning("Rename login '%s' to '%s'", account.login, login)

    u = user.User(
        login=login,
        name=account.name,
        room=room,
        registered_at=account.entrydate,
        account=financeAccount,
        email="{}@wh17.tu-dresden.de".format(account.login),
    )
    session.session.add(u)

    logentry = logging.UserLogEntry(
        author=ru,
        message="User imported from legacy nvtool",
        user=u
    )
    session.session.add(logentry)

    return u


def get_finance_account_for_user(account):
    account_name = "Nutzerkonto von {}".format(account.name)
    financeAccount = finance.Account(name=account_name, type="USER_ASSET")
    return financeAccount


def get_room_for_location(account, building):
    inhabitable, isswitchroom, room_number = get_room_properties(account.location)
    room = session.session.query(facilities.Room).filter(
        (facilities.Room.building == building) &
        (facilities.Room.level == account.location.floor.number) &
        (facilities.Room.number == room_number)).one()
    return room


def get_or_create_root_user(groups):
    root = session.session.query(user.User).filter(user.User.id == 0).scalar()
    if not root is None:
        return root
    else:
        ru = user.User(
            login=ROOT_NAME,
            name="root-User",
            room=None,
            registered_at="2000-01-01",
            account=finance.Account(name="Nutzerkonto von {}".format(ROOT_NAME),
                                    type="USER_ASSET"),
            email="{}@wh17.tu-dresden.de".format(ROOT_NAME),
        )

        ru.passwd_hash = usertools.hash_password(ROOT_PASSWD)
        session.session.add(ru)
        session.session.add(
            user.Membership(user=ru, group=groups["root"], begins_at=null()))
    return ru


def get_room_properties(l):
    if l.comment != "Müllraum":
        number = "0{flat}{room} ({comment})".format(flat=l.flat, room=l.room,
                                                    comment=l.comment)
        inhabitable = True
        isswitchroom = False
    else:
        number = "{comment} {floor}.Etage".format(
            floor=l.floor.number,
            comment=l.comment)
        inhabitable = False
        isswitchroom = True
    return inhabitable, isswitchroom, number


def get_or_create_groups():
    properties_l = []
    resources = {}
    g_d = resources['group'] = {}  # role -> PropertyGroup obj
    log.info("Get or create groups")

    for role, (group_name, properties) in group_props.items():
        q = session.session.query(model.user.Group.id).filter(
            model.user.Group.name == group_name)
        groupexists = session.session.query(q.exists()).scalar()

        if not groupexists:
            log.debug("Create Group %s", group_name)
            g = user.PropertyGroup(name=group_name)
            g_d[role] = g
            for prop_name, modifier in properties.items():
                properties_l.append(user.Property(
                    name=prop_name, property_group=g, granted=modifier))
        else:
            g = session.session.query(model.user.Group).filter(
                model.user.Group.name == group_name).one()
            g_d[role] = g

    trafficGroup = session.session.query(user.TrafficGroup).first()
    if (trafficGroup != None):
        g_d['usertraffic'] = trafficGroup
    else:
        g_d['usertraffic'] = user.TrafficGroup(
            name="Nutzer-Trafficgruppe",
            initial_credit_amount=70 * 2 ** 30,
            credit_amount=10 * 2 ** 30,
            credit_interval=timedelta(days=1),
            credit_limit=21 * 10 * 2 ** 30)

    groups = list(g_d.values()) + properties_l
    session.session.add_all(groups)
    return g_d
