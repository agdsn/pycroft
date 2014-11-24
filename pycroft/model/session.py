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

from datetime import datetime, timedelta
from functools import wraps
from sqlalchemy.orm import create_session, scoped_session
from sqlalchemy import create_engine, func


class DummySessionWrapper(object):
    def __getattr__(self, item):
        # raise Exception("Session not initialized")
        # Workaround for the forking debug server
        init_session()
        return getattr(session, item)


class SessionWrapper(object):
    active = True
    _engine = None

    def __init__(self, autocommit=False, autoflush=True, pooling=True,
                 expire_on_commit=True):

        self._scoped_session = scoped_session(
            lambda: create_session(bind=self._engine,
                                   autocommit=autocommit,
                                   autoflush=autoflush,
                                   expire_on_commit=expire_on_commit))

        self.transaction_log = []

    def __getattr__(self, item):
        if not self.active:
            raise AttributeError, item
        return getattr(self._scoped_session, item)

    def get_engine(self):
        return self._engine

    def init_engine(self, connection_string):
        self._engine = create_engine(connection_string, echo=False)

    def disable_instance(self):
        self.active = False

    #hack for postgres/sqlite "multiplexing"
    def now_sql(self):
        return func.now()


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

def init_session():
    global session
    if isinstance(session, DummySessionWrapper):
        session = SessionWrapper()


def reinit_session(connection_string):
    #required for tests
    global session
    if not isinstance(session, DummySessionWrapper):
        session.disable_instance()
    session = SessionWrapper(pooling=False)
    session.init_engine(connection_string)


session = DummySessionWrapper()
