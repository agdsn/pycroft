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
log = std_logging.getLogger('import')
import random

from tools import timed

import sqlalchemy
from sqlalchemy import create_engine, or_, not_, Integer, func
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.sql.expression import cast
from flask import _request_ctx_stack

from conn import conn_opts
os.environ['PYCROFT_DB_URI'] = conn_opts['pycroft']
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pycroft import model, property
from pycroft.model import (accounting, facilities, dns, user, net, port,
                           finance, session, host, config, logging, types)

import userman_model
import netusers_model
import translate


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


def translate_all(data):
    """Translate legacy data into a list of new objects.

    :param dict data: A dict with keys being the table names and
        values being lists of the legacy ORM objects.

    :returns: The new ORM objects.
    :rtype: list
    """
    objs = []
    resources = {}

    log.info("Generating execution order...")
    for func in translate.reg.sorted_functions():
        log.info("  {func}...".format(func=func.__name__))
        o = func(data, resources)
        log.info("  ...{func} ({details}).".format(
            func=func.__name__,
            details=", ".join(["{}: {}".format(k, v)
                               for k, v in Counter(map(
                                    lambda ob: type(ob).__name__, o)).items()])
        ))
        objs.extend(o)

    return objs


def main(args):
    """Import the legacy data according to ``args``"""
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

        zimmer_hp4108 = session_nu.query(
            netusers_model.Hp4108Port.wheim_id,
            cast(netusers_model.Hp4108Port.etage, Integer).label('etage'),
            netusers_model.Hp4108Port.zimmernr).distinct()

        zimmer_nutzer_zeubor = session_nu.query(
            netusers_model.Nutzer.wheim_id,
            netusers_model.Nutzer.etage,
            netusers_model.Nutzer.zimmernr).filter(or_(
                netusers_model.Nutzer.wheim_id == 12,
                netusers_model.Nutzer.wheim_id == 13)).distinct()

        legacy_data = {
            'wheim': session_nu.query(netusers_model.Wheim).all(),
            'zimmer': zimmer_hp4108.union(zimmer_nutzer_zeubor).all(),
            'nutzer': (session_nu.query(netusers_model.Nutzer)
                       .order_by(netusers_model.Nutzer.nutzer_id).all()),
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

        if args.anonymize:
            translate.anonymize_flag = True
            max_uid = session_nu.query(
                func.max(netusers_model.Nutzer.nutzer_id)).one()[0]
            fr = range(max_uid + 1); to = random.sample(fr, len(fr))
            translate.a_uids.update(zip(fr, to))

            translate.a_rooms.update(zip(
                fr, [random.choice(legacy_data['zimmer']) for i in fr]))

        objs = translate_all(legacy_data)

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
    parser = argparse.ArgumentParser(
        prog='import_legacy', description='fill the hovercraft with eels')
    parser.add_argument("-l", "--log", dest="log_level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO')


    source = parser.add_mutually_exclusive_group()
    source.add_argument("--from-cache", action='store_true')
    source.add_argument("--from-origin", action='store_true')

    parser.add_argument("--bulk", action='store_true', default=False)
    parser.add_argument("--anonymize", action='store_true', default=False)
    #parser.add_argument("--tables", metavar="T", action='store', nargs="+",
    #                choices=cacheable_tables)
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
