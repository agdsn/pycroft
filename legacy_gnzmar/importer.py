#!/usr/bin/env pypy
# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import logging as std_logging
import os
import sys
from datetime import datetime

from sqlalchemy import or_, cast, Date

from legacy_gnzmar.model import PatchRoom, MAC, SwitchPatch
from pycroft import lib, config, model
from pycroft.lib import user as lib_user
from pycroft.lib.logging import log_user_event
from pycroft.lib.user import encode_type2_user_id

log = std_logging.getLogger('import')

from .tools import timed

from sqlalchemy.orm import scoped_session, sessionmaker
from flask import _request_ctx_stack

try:
    from .conn import conn_opts
except ImportError:
    print("Please provide configuration in the legacy_gnzmar/conn.py module.\n"
          "See conn.py.example for the required variables"
          " and further documentation.")
    exit()
os.environ['PYCROFT_DB_URI'] = conn_opts['pycroft']
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pycroft.model import (session, create_engine)

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


def import_data(db_url):
    """Import the legacy data"""
    engine = create_engine(db_url, echo=False)
    session.set_scoped_session(
        scoped_session(sessionmaker(bind=engine),
                       scopefunc=lambda: _request_ctx_stack.top))

    connection_string = conn_opts["gnzmar"]

    engine_ext = create_engine(connection_string, echo=False)
    session_ext = scoped_session(sessionmaker(bind=engine_ext, autoflush=False))

    try:
        with timed(log, thing="Translation"):
            buildings = get_buildings()
            gnz_subnet, mar_subnet = get_subnets()
            root_user = get_root_user()

            for building in buildings:
                log.info("Importing building {}".format(building.short_name))

                if building.short_name == "Gue22":
                    subnet = gnz_subnet
                elif building.short_name == "Mar31":
                    subnet = mar_subnet
                else:
                    raise ImportError("No subnet for building")

                maybe_import_rooms(session_ext, building)
                import_users(session_ext, building, subnet, root_user)

        session.session.commit()
    except Exception as e:
        log.error(e)
        session.session.rollback()
        raise
    finally:
        session.session.close()


def get_buildings():
    existing_buildings = session.session.query(model.facilities.Building).filter(
        or_(model.facilities.Building.short_name == "Gue22",
            model.facilities.Building.short_name == "Mar31")).all()

    if existing_buildings is not None:
        return existing_buildings
    else:
        raise ImportError("No buildings found")

def get_subnets():
    gnz_subnet = session.session.query(model.net.Subnet).filter_by(id=27).one()
    mar_subnet = session.session.query(model.net.Subnet).filter_by(id=26).one()

    log.info("Got subnets")

    return gnz_subnet, mar_subnet


def maybe_import_rooms(session_ext, building):
    log.info("Importing Rooms and Switches")

    oldRooms = session.session.query(model.facilities.Room).filter_by(building=building).all()
    if len(oldRooms) > 5:
        log.info("Rooms already imported")
        #return

    locations = session_ext.query(PatchRoom).filter_by(building=building.id).order_by(PatchRoom.room).all()
    for l in locations:
        log.info("Importing room {}".format(l.room))

        switch = session.session.query(model.host.Switch).join(model.host.Host).join(model.facilities.Room).filter(model.facilities.Room.id == l.switchroom)\
            .filter(model.facilities.Room.building == building).one()

        log.info("Associated switch: {}".format(switch.host.name))

        log.info("Trying to find switch_patch with pp {} and sn {}".format(l.patchport, switch.host.name))

        switch_patch = session_ext.query(SwitchPatch).filter_by(patchport=l.patchport,
                                                                switchname=switch.host.name).one()

        level = 1

        if len(l.room) == 4 or len(l.room) == 6:
            if l.room[1].isnumeric():
                level = int(l.room[1])
        elif len(l.room) == 3 or len(l.room) == 5:
            if l.room[0].isnumeric():
                level = int(l.room[0])

        rnumber = l.room.replace(".", " ")

        #split = l.room.split('.')

        create_room = True

        """
        if len(split) > 1:
            if split[1].isnumeric():
                rnumber = split[0]

                print("SPLIT {}".format(split[1]))

                if split[1] != '1':
                    create_room = False

                    room = session.session.query(model.facilities.Room).filter_by(
                        number=split[0],
                        building=building,
                        level=level
                    ).one()
        """

        if create_room:
            room = model.facilities.Room(
                inhabitable=True,
                building=building,
                level=level,
                number=rnumber,
                address=model.address.Address(
                    street=building.street,
                    number=building.number,
                    addition=rnumber,
                    zip_code="01307",
                )
            )
            building.rooms.append(room)
            log.info('Imported room {}'.format(room.short_name))

        vlan = session.session.query(model.net.VLAN).filter_by(name=building.short_name).one()

        switch_port = model.host.SwitchPort(
            switch=switch,
            name=switch_patch.switchport,
            default_vlans=[vlan]
        )

        log.info("Created switchport {}/{}".format(switch_port.switch.host.name,
                                                   switch_port.name))

        patch_port = model.port.PatchPort(
            name=l.patchport,
            room=room,
            switch_port=switch_port,
            switch_room=switch.host.room
        )

        log.info("Created patchport {}/{} -> {}/{}".format(
            patch_port.room.short_name,
            patch_port.name,
            patch_port.switch_port.switch.host.name,
            patch_port.switch_port.name
        ))

        session.session.add(room)
        session.session.add(switch)
        session.session.add(switch_port)
        session.session.add(patch_port)


def import_users(session_ext, building, subnet, root_user):
    log.info("Import User")

    locations = session_ext.query(PatchRoom).filter_by(building=building.id)

    importcount = 0
    for location in locations:
        # split = location.room.split('.')

        rnumber = location.room.replace(".", " ")

        create = True

        """
        if len(split) > 1:
            if split[1].isnumeric():
                rnumber = split[0]

                if split[1] != '1':
                    create = False
        """

        if create:
            if create_user_with_all_data(rnumber, building,
                                         subnet, root_user,
                                         session_ext):
                importcount += 1

    log.info("Imported {} Users".format(importcount))


def get_room_number(room_desc):
    if room_desc == "Hausmeister":
        return "231"

    return room_desc.replace('Raum ', '')


def create_user_with_all_data(room_name, building,
                              subnet, ru, session_ext):
    session.session.refresh(building)
    session.session.refresh(subnet)

    name = "{}-{}".format(building.short_name, room_name)

    login = name.lower().replace("ä", "ae").replace(" ", "-")

    groups = [config.external_group]

    if session.session.query(model.user.User).filter_by(login=login).first():
        return False

    room = session.session.query(model.facilities.Room).filter_by(building=building,
                                            number=room_name).first()

    patch_ports = session.session.query(model.port.PatchPort).filter_by(room=room).all()

    interfaces = []

    for pp in patch_ports:
        interfaces.append(pp.switch_port.name)

    if not room:
        raise ImportError("room not found for user {}".format(name))

    if not patch_ports:
        raise ImportError("patch ports not found")

    if not interfaces:
        raise ImportError("switch ports not found")

    switch = patch_ports[0].switch_port.switch

    mac = (session_ext.query(MAC)
           .filter_by(router=switch.host.name)
           .filter(MAC.interface.in_(interfaces))
           .order_by(cast(MAC.last_seen, Date).desc())
           .filter(MAC.last_seen != None)
           .first())

    if mac is not None:
        new_user, password = lib_user.create_user(name, login, None, None,
                                                  groups, ru, address=room.address)

        log_user_event("User imported from Güntz/Mar.", ru, new_user)

        log.info("With MAC: {} {}".format(mac.mac, mac.last_seen))

        mac_addr = mac.mac if mac is not None else None

        lib.user.move_in(new_user, room.building.id, room.level, room.number,
                         mac_addr, ru,
                         begin_membership=False, no_birthday_required=True)

        users_plain_password.append((new_user, password))

        log.info("Imported user {}".format(name))

        return bool(new_user)
    else:
        log.warning("No MAC available!")


def get_root_user():
    root = session.session.query(model.user.User).filter(model.user.User.id == 0).scalar()
    if root is None:
        raise ImportError("root user does not exit")
    return root


