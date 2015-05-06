#!/usr/bin/env python2
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from __future__ import print_function

import sys
import operator

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

from conn import conn_opts
import netusers
import userman


old_dbs = (netusers, userman)
cachable_tables = reduce(operator.xor,
                         [{t.__tablename__ for t in old_db.relevant_tables}
                          for old_db in old_dbs])

def drop_cache_db(connection):
    print("Dropping DB 'legacy'")
    connection.execute("DROP DATABASE IF EXISTS legacy")
    connection.execute("COMMIT")


def exists_cache_db(connection):
    exists = connection.execute("SELECT 1 FROM pg_database "
                                "WHERE datname = 'legacy'").first()
    connection.execute("COMMIT")
    return exists is not None


def create_cache_db(connection):
    print("Creating DB 'legacy'")
    connection.execute("CREATE DATABASE legacy")
    connection.execute("COMMIT")


def make_session():
    engine = create_engine(conn_opts['legacy'])
    meta = MetaData(bind=engine)
    session = scoped_session(sessionmaker(bind=engine))

    return session, meta, engine


def cache_relevant_tables_alt(old_db, session, engine):
    # slow
    relevant_tables = old_db.relevant_tables
    ordered_relevant_tables = []
    relevant_actual_tables = map(lambda x: x.__table__, relevant_tables)
    old_db.model.metadata.create_all(bind=engine, tables=relevant_actual_tables)
    sys.stdout.write("Caching " + old_db.name + "...\n")
    for table in old_db.model.metadata.sorted_tables:
        try:
            relevant_i = relevant_actual_tables.index(table)
        except ValueError:
            continue
        else:
            ordered_relevant_tables.append(relevant_tables[relevant_i])

    for source_table in ordered_relevant_tables:
        # source_table is DeclarativeMeta,
        # source_table.__table__ is Table
        name = source_table.__table__.name
        sys.stdout.write("Copying table "+name)
        instances = old_db.session.query(source_table).all()
        n = len(instances)
        for i, instance in enumerate(instances):
            sys.stdout.write("\rCopying "+name+" ("+str(i+1)+"/"+str(n)+")")
            sys.stdout.flush()
            session.merge(instance)
        sys.stdout.write("\n")
        session.commit()
    sys.stdout.write("Finished caching " + old_db.name + "\n")


def cache_relevant_tables(old_db, _, engine, tables=None):
    # > 6x faster, but 'dumb', and requires clean cache
    # old_db.model.metadata.drop_all(engine)

    # type declarative meta
    relevant_tables = [t for t in old_db.relevant_tables
                       if tables is None or t.__tablename__ in tables]
    # type table
    relevant_actual_tables = map(lambda x: x.__table__, relevant_tables)
    if relevant_tables and tables:
        for t in relevant_actual_tables:
            #todo drop in reversed sorted_tables order, and recreate other
            # dropped tables... or just let the user handle it :)
            print("Dropping", t.name)
            t.drop(engine, checkfirst=True)
    old_db.model.metadata.create_all(bind=engine, tables=relevant_actual_tables)

    print("Caching " + old_db.name + "...")
    for table in old_db.model.metadata.sorted_tables:
        if table not in relevant_actual_tables:
            continue
        name = table.name
        print("  " + name, end=" ")
        sys.stdout.flush()
        query = table.select()

        # quick and dirty fix for adjacency list:
        if name == u"finanz_konten":
            print('[ordered adjacency list]', end=" ")
            query = query.order_by("konto_id")

        data = old_db.engine.execute(query).fetchall()
        if data:
            engine.execute(table.insert(), data)
        print("(" + str(len(data)) + ")")
    print("Finished caching " + old_db.name)


def main(tables=None):
    # if 'tables' is None, we cache the full range of tables
    master_engine = create_engine(conn_opts['master'])
    master_connection = master_engine.connect()
    master_connection.execute("COMMIT")
    if tables is None:
        drop_cache_db(master_connection)
    if not exists_cache_db(master_connection):
        if tables:
            print("No cache yet, ignoring tables argument.")
            tables = None
        create_cache_db(master_connection)
    master_connection.close()
    session, meta, engine = make_session()

    for old_db in old_dbs:
        cache_relevant_tables(old_db, session, engine, tables)


if __name__ == "__main__":
    import argparse
    #todo: sql dump anonymized cache so it can survive docker restarts
    parser = argparse.ArgumentParser(prog='cache_legacy')

    parser.add_argument("--tables", metavar="T", action='store', nargs="+",
                        choices=cachable_tables)

    args = parser.parse_args()
    main(**vars(args))
