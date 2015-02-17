#!/usr/bin/env python2
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from subprocess import call
from shlex import split
from sqlalchemy import create_engine, MetaData

from sqlalchemy.orm import scoped_session, sessionmaker

from conn import conn_opts
import netusers
import userman


def drop_cache_db():
    print "Dropping DB", conn_opts["pycroft-legacycache-dbname"]
    call(split("psql -d postgresql://{pycroft-user}@127.0.0.1:{pycroft-port}/postgres -c "
               "\"DROP DATABASE IF EXISTS {pycroft-legacycache-dbname}\"".format(**conn_opts)))

def exists_cache_db():
    return not call(split("psql -d postgresql://{pycroft-user}@127.0.0.1"
                      ":{pycroft-port}/{pycroft-legacycache-dbname} -c ''".format(**conn_opts)))

def create_cache_db():
    print "Creating DB", conn_opts["pycroft-legacycache-dbname"]
    call(split("psql -d postgresql://{pycroft-user}@127.0.0.1:{pycroft-port}/postgres -c "
               "\"CREATE DATABASE {pycroft-legacycache-dbname}\"".format(**conn_opts)))

def make_session():
    engine = create_engine('postgresql://{pycroft-user}@127.0.0.1:{pycroft-port}'
                           '/{pycroft-legacycache-dbname}'.format(**conn_opts))
    meta = MetaData(bind=engine)
    session = scoped_session(sessionmaker(bind=engine))

    return session, meta, engine

def cache_relevant_tables(db, session, engine):
    # TODO: add anonymization option

    db.model.metadata.create_all(engine)
    for source_table in db.model.relevant_tables:
        instances = db.session.query(source_table).all()
        print "Copying",source_table.__table__.name,"("+str(len(instances)),"entries)"
        for instance in instances:
            session.merge(instance)
    session.commit()
    print "Finished caching", db.name

def main(clean_cache=False):
    if clean_cache:
        drop_cache_db()
    if not exists_cache_db():
        create_cache_db()
    session, meta, engine = make_session()

    cache_relevant_tables(netusers,session, engine)
    #cache_relevant_tables(userman, session, engine)

if __name__=="__main__":
    main()
