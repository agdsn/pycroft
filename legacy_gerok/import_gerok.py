#!/usr/bin/env pypy
# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import print_function

import os
import sys
import ipaddr
from collections import Counter
import logging as std_logging
from datetime import timedelta

import legacy_gerok
from legacy_gerok.nvtool_model import Location, Switch, Port, Subnet, Jack, \
    Account, Active

log = std_logging.getLogger('import')
import random

from .tools import timed

import sqlalchemy
from sqlalchemy import create_engine, or_, not_, Integer, func, null
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.expression import cast, exists
from flask import _request_ctx_stack

try:
    from .conn import conn_opts
except ImportError:
    print("Please provide configuration in the legacy/conn.py module.\n"
          "See conn.py.example for the required variables"
          " and further documentation.")
    exit()
os.environ['PYCROFT_DB_URI'] = conn_opts['pycroft']
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pycroft import model, property
from pycroft.model import (traffic, facilities, user, net, port,
                           finance, session, host, config, logging, types)
from pycroft.helpers import user as usertools

from . import nvtool_model
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
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = {}".format(name)).first()
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

    master_engine = create_engine(conn_opts['master'])
    master_connection = master_engine.connect()
    master_connection.execute("COMMIT")

    if args.delete_old:
        log.info("Dropping pycroft db")
        master_connection.execute("DROP DATABASE IF EXISTS pycroft")
        master_connection.execute("COMMIT")
        log.info("Creating pycroft db")
        master_connection.execute("CREATE DATABASE pycroft")
        master_connection.execute("COMMIT")
        log.info("Creating pycroft model schema")
        model.create_db_model(engine)

    with timed(log, thing="Translation"):
        bank_financeAccount = finance.Account(name="Bankkonto Ger", type="BANK_ASSET")
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

        building = create_site_and_building()
        ger38subnet, sn = create_subnet(session_nvtool)
        import_facilities_and_switches(session_nvtool, building, ger38subnet)
        import_SwitchPatchPorts(session_nvtool, building, sn)
        groups = get_or_create_groups()
        fee_account = ensure_config(groups)
        import_users(session_nvtool, building, groups, ger38subnet, fee_account, bank_account)

        session.session.commit()

def ensure_config(g_d):

    conf = session.session.query(config.Config).first()
    if conf is None:
        fee_account = finance.Account(name="Beiträge", type="REVENUE")
        session.session.add(fee_account)

        con = config.Config(
            member_group=g_d["member"],
            violation_group=g_d["suspended"],
            network_access_group=g_d["member"],  # todo: actual network_access_group
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


def import_SwitchPatchPorts(session_nvtool, building, sn):
    # As on the last check (2017-09-03) there are no active cables to jacks with other numbers.
    # After cabeling to gigabit no userport was left and the stystemports are not in use.
    jacks = session_nvtool.query(Jack).filter(
        (Jack.number == 1) & (Jack.subnet == sn))
    for j in jacks:
        switch = session.session.query(host.Switch).filter(host.Switch.management_ip == j.port.switch.ip).one()
        interface = next(
            i for i in switch.switch_interfaces if i.name == str(j.port.number))

        inhabitable, isswitchroom, room_number = GetRoomProperties(j.location)

        room = session.session.query(facilities.Room).filter(
            (facilities.Room.building == building) &
            (facilities.Room.level == j.location.floor.number) &
            (facilities.Room.number == room_number)).one()
        spp = port.SwitchPatchPort(
            room=room,
            switch_interface=interface,
            name="{flat}{room}".format(flat=j.location.flat,
                                       room=j.location.room, )
        )
        session.session.add(spp)


def create_site_and_building():
    site = facilities.Site(
        name="Gerokstraße"
    )
    building = facilities.Building(
        site=site,
        short_name="Ger",
        street="Gerokstraße",
        number="38")
    return building


def create_subnet(session_nvtool):
    # Exclude Ger27
    sn = session_nvtool.query(Subnet).filter(Subnet.id != 1).one()
    ger38subnet = net.Subnet(
        address=sn.network,
        gateway=sn.gateway,
        vlan=net.VLAN(
            name="Hausnetz Ger38",
            vid=38
        )
    )

    return ger38subnet, sn


def import_facilities_and_switches(session_nvtool, building, ger38subnet):
    # Only Gerok 38 locations
    locations = session_nvtool.query(Location).filter(Location.domain_id == 2)
    for l in locations:
        inhabitable, isswitchroom, number = GetRoomProperties(l)

        room = facilities.Room(
            inhabitable=inhabitable,
            building=building,
            level=l.floor.number,
            number=number
        )
        building.rooms.append(room)

        if(isswitchroom):
            switches = session_nvtool.query(Switch).filter(Switch.location == l)
            for s in switches:
                switch = host.Switch(
                    name = s.comment,
                    management_ip = s.ip,
                    room = room
                )
                ports = session_nvtool.query(Port).filter(Port.switch == s)
                for p in ports:
                    port = host.SwitchInterface(
                        name = p.number,
                        subnets = [ger38subnet],
                        mac = "00:00:00:00:00:38" #DGS-3100 are L2 Switches they don't have a mac for interfaces
                    )
                    switch.switch_interfaces.append(port)

                session.session.add(switch)

    session.session.add(building)
    session.session.commit()


def import_users(session_nvtool, building, groups, ger38subnet, fee_account, bank_account):

    root = session.session.query(user.Membership).filter(user.Membership.id == 0)
    if not session.session.query(root.exists()).scalar():
        ru = user.User(
            login=ROOT_NAME,
            name="root-User",
            room=None,
            registered_at="2000-01-01",
            account=finance.Account(name="Nutzerkonto von {}".format(ROOT_NAME), type="USER_ASSET"),
            email="{}@wh17.tu-dresden.de".format(ROOT_NAME),
        )

        ru.passwd_hash = usertools.hash_password(ROOT_PASSWD)
        session.session.add(ru)
        session.session.add(user.Membership(user=ru, group=groups["root"], begins_at=null()))

    ger38locations = session_nvtool.query(Location.id).filter(Location.domain_id == 2)
    legacy_accounts = session_nvtool.query(Account).filter(Account.location_id.in_(ger38locations))
    for account in legacy_accounts:
        login = account.login
        if not user.User.login_regex.match(account.login):
            login = "user_{}".format(account.id)
            log.warning("Rename login '%s' to '%s'", account.login, login)

        inhabitable, isswitchroom, room_number = GetRoomProperties(account.location)
        room = session.session.query(facilities.Room).filter(
                (facilities.Room.building == building) &
                (facilities.Room.level == account.location.floor.number) &
                (facilities.Room.number == room_number)).one()

        account_name = "Nutzerkonto von {}".format(account.name)

        financeAccount = finance.Account(name=account_name, type="USER_ASSET")
        u = user.User(
            login=login,
            name=account.name,
            room=room,
            registered_at= account.entrydate,
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

        for trans in account.financetransactions:
            # Mitgliesbeitrag
            if trans.banktransfer is not None:
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
                    account=financeAccount,
                    transaction=transaction
                )
            if trans.fee is not None:
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
                    account=financeAccount,
                    transaction=transaction
                )

            session.session.add(transaction)
            session.session.add(credit_split)
            session.session.add(debit_split)


        if "Hausmeister" not in account.name:
            usergroupmember = user.Membership(user=u, group=groups["member"], begins_at=account.entrydate)
        else:
            usergroupmember = user.Membership(user=u, group=groups["caretaker"], begins_at=account.entrydate)
        session.session.add(usergroupmember)

        active = session_nvtool.query(Active).filter(Active.account == account).one_or_none()

        if not active is None:
            if active.activegroup_id == 10: #oldstaff
                oldstaff = user.Membership(user=u, group=groups["org"], begins_at=account.entrydate, ends_at=account.entrydate+timedelta(days=1))
                session.session.add(oldstaff)
            else:
                staff = user.Membership(user=u, group=groups["org"],
                                           begins_at=account.entrydate)
                session.session.add(staff)

        for legacy_host in account.hosts:
            mac = legacy_host.mac
            hostLocation=mac.jack.location
            inhabitable, isswitchroom, room_number = GetRoomProperties(hostLocation)
            hostroom = session.session.query(facilities.Room).filter(
                (facilities.Room.building == building) &
                (facilities.Room.level == hostLocation.floor.number) &
                (facilities.Room.number == room_number)).one()

            if room != hostroom and "Müllraum" in hostroom.number:
                h = host.ServerHost(owner=u, room=hostroom, name="Server of {}".format(u.name))
                interface = host.ServerInterface(host=h, mac=mac.macaddr)
            else:
                h = host.UserHost(owner=u, room=room)
                interface = host.UserInterface(host=h, mac=mac.macaddr)


            address = ipaddr.IPv4Network(mac.ip.ip).ip
            ip = host.IP(interface=interface,
                         address=address,
                         subnet=ger38subnet)
            session.session.add(ip)








def GetRoomProperties(l):
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
    # TODO: create other groups

    configgroups = group_props.items()
    for role, (group_name, properties) in configgroups:
        q = session.session.query(model.user.Group.id).filter(
            model.user.Group.name == group_name)
        groupexists = session.session.query(q.exists()).scalar()

        if (not groupexists):
            g = user.PropertyGroup(name=group_name)
            g_d[role] = g
            for prop_name, modifier in properties.items():
                properties_l.append(user.Property(
                    name=prop_name, property_group=g, granted=modifier))
        else:
            g = session.session.query(model.user.Group).filter(
                model.user.Group.name == group_name)
            g_d[role] = g

    g_d['usertraffic'] = user.TrafficGroup(
        name="Nutzer-Trafficgruppe",
        credit_amount=3 * 2 ** 30,
        credit_interval=timedelta(days=1),
        credit_limit=21 * 3 * 2 ** 30)

    groups = list(g_d.values()) + properties_l
    session.session.add_all(groups)
    return g_d

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog='import_nvtool', description='fill the hovercraft with more eels')
    parser.add_argument("-l", "--log", dest="log_level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO')

    parser.add_argument("--delete-old", action='store_true', default=True)

    args = parser.parse_args()

    import_log_fname = "import.log"
    sqlalchemy_log_fname = "import.sqlalchemy.log"

    log.info("Logging to %s and %s"%(import_log_fname, sqlalchemy_log_fname))

    log_fmt = '[%(levelname).4s] %(name)s:%(funcName)s:%(message)s'
    formatter = std_logging.Formatter(log_fmt)
    std_logging.basicConfig(level=std_logging.DEBUG,
                            format=log_fmt,
                            filename=import_log_fname,
                            filemode='w')
    console = std_logging.StreamHandler()
    console.setLevel(getattr(std_logging, args.log_level))
    console.setFormatter(formatter)
    std_logging.getLogger('').addHandler(console)

    sqlalchemy_loghandler = std_logging.FileHandler(sqlalchemy_log_fname)
    std_logging.getLogger('sqlalchemy').addHandler(sqlalchemy_loghandler)
    sqlalchemy_loghandler.setLevel(std_logging.DEBUG)

    main(args)
    log.info("Import finished.")
