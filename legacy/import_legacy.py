#!/usr/bin/env python2
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import os
import sys

from sqlalchemy import create_engine, distinct
from sqlalchemy.orm import scoped_session, sessionmaker
from flask import _request_ctx_stack

from conn import conn_opts
import userman_model
import netusers_model
from userman import relevant_tables as tables_um
from netusers import relevant_tables as tables_nu

os.environ['PYCROFT_DB_URI'] = conn_opts['pycroft']

#so pycroft imports work:
#sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ..pycroft import model
from ..pycroft.model import facilities, net, port, session


def exists_db(connection, name):
    exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = {}".format(name)).first()
    connection.execute("COMMIT")

    return exists is not None


def import_dormitories():
    buildings = session_nu.query(netusers_model.Wheim).all()
    b_d = {}
    print "importing", len(buildings), "buildings"
    for _b in buildings:
        b = facilities.Dormitory(short_name=_b.kuerzel,
                                 street=_b.str,
                                 number=_b.hausnr)
        session.session.add(b)
        b_d[_b.wheim_id] = b
    session.session.commit()

def import_rooms():
    rooms = session_nu.query(netusers_model.Hp4108Port).all()
    print "importing", len(rooms), "rooms"
    for _r in rooms:
        r = facilities.Room(dormitory=b_d[_r.wheim_id],
                            level=_r.etage,
                            number=_r.zimmernr,
                            inhabitable=True)
        session.session.add(r)
    session.session.commit()

def main(clean_pycroft=True):
    # think about this:
    #  move model translation functions to netusers and userman module?
    engine = create_engine(os.environ['PYCROFT_DB_URI'], echo=False)
    session.set_scoped_session(
        scoped_session(sessionmaker(bind=engine),
                       scopefunc=lambda: _request_ctx_stack.top))

    print "Creating pycroft model schema"
    model.create_db_model()


    engine_nu = create_engine(conn_opts["legacy"], echo=False)
    session_nu = scoped_session(sessionmaker(bind=engine_nu))

    master_engine = create_engine(conn_opts['master'])
    master_connecton = master_engine.connect()

    if clean_pycroft:
        master_connection.execute("DROP DATABASE IF EXISTS pycroft")
        master_connection.execute("COMMIT")
    if not exists_db(master_connecton, "pycroft"):
        master_connecton.execute("CREATE DATABASE pycroft")
        master_connecton.execute("COMMIT")

if __name__=="__main__":
    main()
