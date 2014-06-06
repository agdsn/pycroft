# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.session
    ~~~~~~~~~~~~~~

    This module contains the session stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine, pool, func
from functools import wraps


class DummySession(object):
    def __getattr__(self, item):
        # raise Exception("Session not inizialized")
        # Workaround for the forking debug server
        init_session()
        return getattr(session, item)


class SessionWrapper(object):
    active = True

    def __init__(self, autocommit=False, autoflush=True, connection_string=None, pooling=True):
        if connection_string is None:
            connection_string = "sqlite:////tmp/test.db"

        self._engine = create_engine(connection_string, echo=False)
        self._scoped_session = scoped_session(
                                sessionmaker(bind=self._engine,
                                             autocommit=autocommit,
                                             autoflush=autoflush))

        self.transaction_log = []

    def __getattr__(self, item):
        if not self.active:
            raise AttributeError, item
        return getattr(self._scoped_session, item)

    def get_engine(self):
        return self._engine

    def disable_instance(self):
        self.active = False

    # hack for postgres/sqlite "multiplexing"
    def now_sql(self):
        if self._engine.driver == "psycopg2":
            return func.now()
        else:
            # 1 Minute modifier to fix strange unit test race
            return func.datetime("now", "+1 minutes")


def with_transaction(f):

    # Need to define session global here so that it is also available
    # in the wrapper function defined below.
    global session

    @wraps(f)
    def helper(*args, **kwargs):
        global session

        # We need to check whether there is already a transaction in the log
        # because if there is no one, no new transaction should be started.
        if not session.transaction_log:
            transaction = session
        else:
            transaction = session.begin(subtransactions=True)

        session.transaction_log.append(transaction)

        try:
            ret = f(*args, **kwargs)
            transaction.commit()
        except:
            transaction.rollback()
            raise
        finally:
            session.transaction_log.pop()

        return ret

    return helper


def init_session(connection_string=None):
    global session
    if isinstance(session, DummySession):
        session = SessionWrapper(connection_string=connection_string)


def reinit_session(connection_string=None):
    global session

    if not isinstance(session, DummySession):
        session.disable_instance()
    session = SessionWrapper(connection_string=connection_string, pooling=False)


session = DummySession()
