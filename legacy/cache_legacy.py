#!/usr/bin/env python2
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import sys
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker

from conn import conn_opts
import netusers
import userman


def drop_cache_db(connection):
    connection.execute("DROP DATABASE IF EXISTS legacy")
    connection.execute("COMMIT")


def exists_cache_db(connection):
    exists = connection.execute("SELECT 1 FROM pg_database "
                                "WHERE datname = 'legacy'").first()
    connection.execute("COMMIT")
    return exists is not None


def create_cache_db(connection):
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


def cache_relevant_tables(old_db, _, engine):
    # TODO: add anonymization option
    # > 6x faster, but 'dumb', and requires clean cache
    # old_db.model.metadata.drop_all(engine)
    relevant_tables = old_db.relevant_tables
    relevant_actual_tables = map(lambda x: x.__table__, relevant_tables)
    old_db.model.metadata.create_all(bind=engine, tables=relevant_actual_tables)
    print "Caching " + old_db.name + "..."
    for table in old_db.model.metadata.sorted_tables:  # tables:
        if table not in relevant_actual_tables:
            continue
        name = table.name
        print "Copying table " + name,
        sys.stdout.flush()
        query = table.select()

        # quick and dirty fix for adjacency list:
        if name == u"finanz_konten":
            print '[mit extrawurst]',
            query = query.order_by("konto_id")

        data = old_db.engine.execute(query).fetchall()
        if data:
            engine.execute(table.insert(), data)
        print "(" + str(len(data)) + ")"
    print "Finished caching " + old_db.name


def main(clean_cache=True):
    master_engine = create_engine(conn_opts['master'])
    master_connection = master_engine.connect()
    master_connection.execute("COMMIT")
    if clean_cache:
        drop_cache_db(master_connection)
    if not exists_cache_db(master_connection):
        create_cache_db(master_connection)
    master_connection.close()
    session, meta, engine = make_session()

    cache_relevant_tables(netusers, session, engine)
    cache_relevant_tables(userman, session, engine)


if __name__ == "__main__":
    main()
