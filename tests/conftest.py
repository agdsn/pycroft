#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from typing import cast

import pytest
from coverage.annotate import os
from sqlalchemy import event
from sqlalchemy.ext.declarative import DeferredReflection
from sqlalchemy.future import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import SingletonThreadPool

from pycroft.model import drop_db_model, create_db_model
from pycroft.model.session import set_scoped_session, Session


@pytest.fixture(scope='session')
def engine():
    try:
        uri = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLalchemy connection string.")
    return create_engine(uri, poolclass=SingletonThreadPool, future=True)


@pytest.fixture(scope='session')
def clean_engine(engine):
    connection = engine.connect()
    drop_db_model(connection)
    create_db_model(connection)
    connection.commit()
    return engine


@pytest.fixture
def connection(clean_engine):
    engine = clean_engine
    connection = engine.connect()
    # this turns our connection into „transactional state“
    # henceforth, every session binding to this connection will participate in this transaction.
    # see https://docs.sqlalchemy.org/en/14/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites
    transaction = connection.begin()  # outer, non-ORM transaction
    DeferredReflection.prepare(engine)

    yield connection

    transaction.rollback()
    connection.close()


@pytest.fixture()
def session(connection):
    """Provides a session to a created database.

    Rolled back after use
    """
    nested = connection.begin_nested()
    s = scoped_session(sessionmaker(bind=connection, future=True))
    set_scoped_session(s)
    session = cast(Session, s())

    # see the comment above
    @event.listens_for(session, "after_transaction_end")
    def end_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    # close_all_sessions()
    session.rollback()
    Session.remove()
    # if the transaction is still associated, this means it has e.g. pending trigger events.
    transaction_associated = nested.connection._transaction == nested
    if transaction_associated:
        nested.rollback()
