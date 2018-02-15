#!/usr/bin/env python3
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.


import sys
import operator

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from functools import reduce

# This is a fix I'm not proud of, but it prevents a partial and thus
# corrupt declaration of pycroft-model-classes which happens
# implicitly whenever you import from pycroft.$module, as
# pycroft.__init__ import the config which needs the pycroft model
from pycroft.model import _all


try:
    from .conn import conn_opts
except ImportError:
    print("Please provide configuration in the legacy/conn.py module.\n"
          "See conn.py.example for the required variables"
          " and further documentation.")
    exit()

# cache_ldap make use of conn, so importing later
from .cache_ldap import cache_ldap, create_ldap_tables
from . import netusers
from . import userman


old_dbs = (netusers, userman)
cacheable_tables = reduce(operator.xor,
                         [{t.__tablename__ for t in old_db.relevant_tables}
                          for old_db in old_dbs])


def make_session():
    engine = create_engine(conn_opts['legacy'])
    meta = MetaData(bind=engine)
    session = scoped_session(sessionmaker(bind=engine))

    return session, meta, engine


def cache_relevant_tables_alt(old_db, session, engine):
    # slow
    relevant_tables = old_db.relevant_tables
    ordered_relevant_tables = []
    relevant_actual_tables = [x.__table__ for x in relevant_tables]
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
    relevant_metas = [t for t in old_db.relevant_tables
                       if tables is None or t.__tablename__ in tables]
    # type table
    relevant_tables = [x.__table__ for x in relevant_metas]
    if relevant_metas and tables:
        for t in relevant_tables:
            #todo drop in reversed sorted_tables order, and recreate other
            # dropped tables... or just let the user handle it :)
            print("Dropping", t.name)
            t.drop(engine, checkfirst=True)
    old_db.model.metadata.create_all(bind=engine, tables=relevant_tables)

    print("Caching " + old_db.name + "...")
    for table in old_db.model.metadata.sorted_tables:
        if table not in relevant_tables:
            continue
        print("  " + table.name, end=" ")
        sys.stdout.flush()
        query = table.select()

        # quick and dirty fix for adjacency list:
        if table.name == u"finanz_konten":
            print('[ordered adjacency list]', end=" ")
            query = query.order_by("konto_id")

        data = old_db.engine.execute(query).fetchall()
        if data:
            engine.execute(table.insert(), data)
        print("(" + str(len(data)) + ")")
    print("Finished caching " + old_db.name)


def cache_legacy(tables=None, sql_only=True, ldap_only=False):
    # if 'tables' is None, we cache the full range of tables
    engine = create_engine(conn_opts['legacy'])
    connection = engine.connect()
    connection.execute("COMMIT")
    if tables is None:
        print("Dropping schema public")
        connection.execute("DROP SCHEMA IF EXISTS public CASCADE")
        connection.execute("COMMIT")
        print("Recreating schema public")
        connection.execute("CREATE SCHEMA public")
        connection.execute("COMMIT")
    connection.close()

    session, meta, engine = make_session()

    for old_db in old_dbs if not ldap_only else []:
        cache_relevant_tables(old_db, session, engine, tables)

    if not sql_only:
        create_ldap_tables(engine=engine)
        cache_ldap(session=session)

def main():
    import argparse
    #todo: sql dump anonymized cache so it can survive docker restarts
    parser = argparse.ArgumentParser(prog='cache_legacy')

    parser.add_argument("--tables", metavar="T", action='store', nargs="+",
                        choices=cacheable_tables)
    parser.add_argument("--ldap-only", action='store_true')
    parser.add_argument("--sql-only", action='store_true')
    args = parser.parse_args()
    cache_legacy(**vars(args))


if __name__ == '__main__':
    main()
