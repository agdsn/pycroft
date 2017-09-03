#!/usr/bin/env pypy
# coding=utf-8
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import print_function

import os
import sys
from collections import Counter
import logging as std_logging

from legacy_gerok.nvtool_model import Location, Switch, Port, Subnet, Jack

log = std_logging.getLogger('import')
import random

from .tools import timed

import sqlalchemy
from sqlalchemy import create_engine, or_, not_, Integer, func
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.expression import cast
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

from . import nvtool_model

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

        building = create_site_and_building()
        ger38subnet, sn = create_subnet(session_nvtool)
        import_facilities_and_switches(session_nvtool, building, ger38subnet)
        import_SwitchPatchPorts(session_nvtool, building, sn)

        session.session.commit()



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
