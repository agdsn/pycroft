#!/usr/bin/env pypy
# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import logging as std_logging
import os
import sys

import ipaddr

from legacy_hoy.hoy_model import Room, User, Ip
from pycroft import lib, config, model
from pycroft.lib import user as lib_user
from pycroft.lib.logging import log_user_event
from pycroft.lib.user import encode_type2_user_id

log = std_logging.getLogger('import')

from .tools import timed

from sqlalchemy import create_engine, null
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import _request_ctx_stack

try:
    from .conn import conn_opts
except ImportError:
    print("Please provide configuration in the legacy_hoy/conn.py module.\n"
          "See conn.py.example for the required variables"
          " and further documentation.")
    exit()
os.environ['PYCROFT_DB_URI'] = conn_opts['pycroft']
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pycroft.model import (session)

ROOT_NAME = "agdsn"

users_plain_password = []


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


def import_hoy(db_url):
    """Import the legacy data"""
    engine = create_engine(db_url, echo=False)
    session.set_scoped_session(
        scoped_session(sessionmaker(bind=engine),
                       scopefunc=lambda: _request_ctx_stack.top))

    connection_string_hoy = conn_opts["hoy"]

    engine_hoy = create_engine(connection_string_hoy, echo=False)
    session_hoy = scoped_session(sessionmaker(bind=engine_hoy))

    try:

        with timed(log, thing="Translation"):
            building = get_or_create_site_and_building()
            hyo10subnet = create_subnet()
            root_user = get_root_user()
            maybe_import_rooms(session_hoy, building)
            import_users(session_hoy, building, hyo10subnet, root_user)

            import csv
            with open('./hoy10_users.csv', 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',',
                                        quotechar='"',
                                        quoting=csv.QUOTE_MINIMAL)
                for (user, password) in users_plain_password:
                    writer.writerow([encode_type2_user_id(user.id), user.name, user.room.short_name, user.login, password])

        session.session.commit()
    except Exception as e:
        log.error(e)
        session.session.rollback()
        raise
    finally:
        session.session.close()


def get_or_create_site_and_building():

    existing_building = session.session.query(model.facilities.Building).filter(
        model.facilities.Building.short_name == "Hoy10").scalar()
    if existing_building is not None:
        return existing_building

    traffic_group = session.session.query(model.user.TrafficGroup).first()

    site = model.facilities.Site(
        name="Hoyerswerdaerstraße"
    )
    building = model.facilities.Building(
        site=site,
        short_name="Hoy10",
        street="Hoyerswerdaerstraße",
        number="10",
        default_traffic_group=traffic_group)

    log.info("Created Site and Building")
    return building


def create_subnet():
    hoy10subnet = model.net.Subnet(
        description="Hoy10",
        address=ipaddr.IPNetwork("141.76.119.0/25"),
        gateway=ipaddr.IPAddress("141.76.119.1"),
        reserved_addresses_bottom=4,
        vlan=model.net.VLAN(
            name="Hoy10",
            vid=3
        )
    )

    log.info("Created Subnet with Vlan")

    return hoy10subnet


def maybe_import_rooms(session_hoy, building):
    log.info("Importing Rooms and Switches")

    oldRooms = session.session.query(model.facilities.Room).filter(model.facilities.Room.building == building).all()
    if oldRooms:
        log.info("Rooms already imported")
        return

    locations = session_hoy.query(Room)
    for l in locations:
        room = model.facilities.Room(
            inhabitable=True,
            building=building,
            level=l.etage,
            number=get_room_number(l.room_desc)
        )
        building.rooms.append(room)
        log.info('Imported room {}'.format(room.short_name))

    session.session.add(building)


def import_users(session_hoy, building, hoy10subnet, root_user):
    log.info("Import User")

    legacy_accounts = session_hoy.query(User).filter(User.online_to > session.utcnow()).filter(User.email != "")

    importcount = 0
    for account in legacy_accounts:
        if create_user_with_all_data(account, building,
                                  hoy10subnet, root_user,
                                  session_hoy):
          importcount +=1

    log.info("Imported {} Users".format(importcount))


def get_room_number(room_desc):
    if room_desc == "Hausmeister":
        return "231"

    return room_desc.replace('Raum ', '')


def create_user_with_all_data(account, building,
                              hoy10subnet, ru, session_hoy):
    name = "{} {}".format(account.firstname, account.lastname)
    email = account.email.lower()
    login = email.split("@")[0].replace('_', '.')
    groups = [config.external_group]

    if login == "hoy10":
        login = "hausmeister-hoy10"
        groups = [config.caretaker_group]

    if session.session.query(model.user.User).filter_by(login=login).first():
        return False

    new_user, password = lib_user.create_user(name, login, email, None, groups, ru)

    log_user_event("User imported from legacy hoy", ru, new_user)

    if account.mycomment:
        log_user_event(account.mycomment, ru, new_user)

    log.info("Imported user {}".format(email))

    ip = session_hoy.query(Ip).filter(Ip.user == account).first()

    room = session.session.query(model.facilities.Room).filter_by(building=building,
                                            level=account.room.etage,
                                            number=get_room_number(account.room.room_desc)).first()

    if not room:
        raise ImportError("room not found for user {}".format(account.email))

    if not ip:
        log.warning("ip not found for user, ignoring".format(account.email))
        return False

    lib.user.move_in(new_user, room.building, room.level, room.number, ip.mac, ru,
                     ip_address=ipaddr.IPAddress(ip.ip), subnet=hoy10subnet, begin_membership=False)

    users_plain_password.append((new_user, password))

    return bool(new_user)


def get_root_user():
    root = session.session.query(model.user.User).filter(model.user.User.id == 0).scalar()
    if root is None:
        raise ImportError("root user does not exit")
    return root


