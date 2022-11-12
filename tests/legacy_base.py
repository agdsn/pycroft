#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import logging
import os
import unittest
import warnings
from contextlib import contextmanager
from typing import cast

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import DeferredReflection
from sqlalchemy.orm import Session, scoped_session, sessionmaker, \
    close_all_sessions
from sqlalchemy.pool import SingletonThreadPool

from pycroft import Config
from pycroft.model import create_engine, drop_db_model, create_db_model, session
from tests.factories import ConfigFactory

engine = None
connection = None
_setup_stack = 0


def setup():
    global engine, connection, _setup_stack
    if _setup_stack > 0:
        return
    try:
        uri = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLalchemy connection string.")

    engine = create_engine(uri, poolclass=SingletonThreadPool, future=True)

    connection = engine.connect()

    drop_db_model(connection)
    create_db_model(connection)
    connection.commit()

    DeferredReflection.prepare(engine)
    _setup_stack += 1


def get_engine_and_connection():
    global engine, connection
    return engine, connection


def teardown():
    global engine, connection, _setup_stack
    _setup_stack -= 1
    if _setup_stack != 0:
        return
    assert isinstance(connection, Connection)
    connection.commit()  # necessary to apply e.g. pending triggers
    drop_db_model(connection)
    connection.close()
    engine = None
    connection = None


@pytest.mark.legacy
class SQLAlchemyTestCase(unittest.TestCase):
    """Base class for test cases that require an initialized database

    Tests will executed inside a nested transaction using SAVEPOINTs before each
    test is test executed. Tests are rolled back after execution regardless of
    their outcome.
    """
    def __init__(self, *a, **kw):
        warnings.warn('Use pytest with the `session` fixture instead of SQLAlchemyTestCase',
                      DeprecationWarning)
        super().__init__(*a, **kw)

    session: Session

    @classmethod
    def setUpClass(cls):
        setup()

    @classmethod
    def tearDownClass(cls):
        teardown()

    def setUp(self):
        super().setUp()
        assert isinstance(connection, Connection)
        self.transaction = connection.begin_nested()
        s = scoped_session(sessionmaker(bind=connection))
        session.set_scoped_session(s)
        self.session = cast(Session, s())
        self.addCleanup(self.cleanup)

    def _rollback(self):
        # Rollback the session (automatically rolls back the transaction if it is associated)
        session.session.rollback()
        session.Session.remove()
        assert self.transaction is not None
        # if the transaction is still associated, this means it has e.g. pending trigger events.
        transaction_associated = self.transaction.connection._transaction == self.transaction
        if transaction_associated:
            self.transaction.rollback()
        self.transaction = None

    def tearDown(self):
        if self.transaction is not None:
            self._rollback()
        close_all_sessions()
        super().tearDown()

    def cleanup(self):
        if self.transaction is None:
            return
        self._rollback()

    @contextmanager
    def _rollback_with_context(self, context):
        with context:
            try:
                yield context
            except:
                # Check if the session is in “partial rollback” state
                if not session.session.is_active:
                    session.session.rollback()
                raise

    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        context = super().assertRaises(excClass)
        if callableObj is None:
            return self._rollback_with_context(context)
        with self._rollback_with_context(context):
            callableObj(*args, **kwargs)

    def assertRaisesRegexp(self, expected_exception, expected_regexp,
                           callable_obj=None, *args, **kwargs):
        context = super().assertRaisesRegex(expected_exception, expected_regexp)
        if callable_obj is None:
            return self._rollback_with_context(context)
        with self._rollback_with_context(context):
            callable_obj(*args, **kwargs)

    @contextmanager
    def assertUniqueViolation(self, message):
        pattern = 'duplicate key value violates unique constraint ".+_key"'
        with self.assertRaisesRegex(IntegrityError, pattern, msg=message) as cm:
            yield cm

    @staticmethod
    def assert_object_persistent(object):
        assert inspect(object).persistent



