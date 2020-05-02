# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import logging
from contextlib import contextmanager
from functools import partial
import os
import random
import string
import unittest
from flask import url_for, _request_ctx_stack
import flask_testing as testing
from fixture.style import NamedDataStyle
from fixture import SQLAlchemyFixture, DataTestCase
from fixture.util import start_debug, stop_debug
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.session import close_all_sessions
from sqlalchemy.pool import SingletonThreadPool
import sys

from tests.factories import ConfigFactory, UserFactory, AdminPropertyGroupFactory, MembershipFactory
from werkzeug.routing import IntegerConverter, UnicodeConverter
from pycroft.model import session, create_engine
from pycroft.model import _all, drop_db_model, create_db_model

from sqlalchemy import event

engine = None
connection = None
_setup_stack = 0

import logging
logger = logging.getLogger('pyctest')
import traceback


OUR_FILES_PREFIX = "/opt/pycroft/app/"
def setup():
    global engine, connection, _setup_stack
    _setup_stack += 1
    if _setup_stack > 1:
        return

    logger.setLevel(logging.DEBUG)
    # logging.getLogger('sqlalchemy').setLevel(logging.INFO)
    # logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
    # logging.getLogger('sqlalchemy.orm').setLevel(logging.INFO)

    try:
        uri = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLalchemy connection string.")
    engine = create_engine(uri, poolclass=SingletonThreadPool)

    connection = engine.connect()
    drop_db_model(connection)  # TODO do they use a session here?
    create_db_model(connection)
    # standard decorator style
    @event.listens_for(engine, 'do_execute')
    def receive_do_execute(_cursor, statement: str, _parameters, _context):
        "listen for the 'do_execute' event"
        logger.debug("EXECUTE '%s'. Stack info: %s", statement.split()[0], stack_info())

def add_session_event_listeners(session):
    @event.listens_for(_all.RoomHistoryEntry.room_id, 'set', propagate=True)
    @event.listens_for(_all.RoomHistoryEntry.room, 'set', propagate=True)
    def trace_room_id_set(target, value, initiator, *args, **kwargs):
        logger.debug("SET %s=%s by %s. Stack info: %s",
                     target, value, initiator, stack_info())
        if kwargs:
            logger.debug("  KWARGS: %s", kwargs)

        if args:
            logger.debug("  ARGS: %s", args)

    for ev in ['transient_to_pending',
               'pending_to_persistent',
               'deleted_to_persistent',
               'detached_to_persistent',
               'loaded_as_persistent',
            ]:
        @event.listens_for(session, ev)
        def tracer(session, obj):
            logger.debug("SESSION_EVENT %s: %r", ev, obj)


def stack_info():
    our_frames = [
        f for f in traceback.extract_stack()
        if f.filename.startswith(OUR_FILES_PREFIX)
    ]

    if not our_frames:
        return '(now owned stackframe)'
    f = our_frames[0]
    filename = f.filename.split(OUR_FILES_PREFIX, 1)[-1]
    return f"{f.name} in {filename}:{f.lineno}"


def get_engine_and_connection():
    global engine, connection
    return engine, connection


def teardown():
    global engine, connection, _setup_stack
    _setup_stack -= 1
    if _setup_stack > 0:
        return
    drop_db_model(connection)
    connection.close()
    engine = None
    connection = None


class SQLAlchemyTestCase(unittest.TestCase):
    """Base class for test cases that require an initialized database

    Tests will executed inside a nested transaction using SAVEPOINTs before each
    test is test executed. Tests are rolled back after execution regardless of
    their outcome.
    """
    @classmethod
    def setUpClass(cls):
        setup()

    @classmethod
    def tearDownClass(cls):
        teardown()

    def setUp(self):
        super(SQLAlchemyTestCase, self).setUp()
        self.transaction = connection.begin_nested()
        s = scoped_session(sessionmaker(bind=connection))
        logger.debug(f"SETTING SESSION {s}")
        session.set_scoped_session(s)
        add_session_event_listeners(s)
        self.addCleanup(self.cleanup)

    def _rollback(self):
        logger.debug("_ROLLBACK")
        # Rollback the session
        session.session.rollback()
        logger.debug("  -> calling Session.remove()")
        session.Session.remove()
        # Rollback the outer transaction to the savepoint
        logger.debug("  -> calling transaction.rollback()")
        self.transaction.rollback()
        logger.debug("  -> done calling transaction.rollback()")
        self.transaction = None
        # breakpoint()

    def tearDown(self):
        logger.debug("TEARDOWN")
        self._rollback()
        close_all_sessions()
        super(SQLAlchemyTestCase, self).tearDown()

    def cleanup(self):
        logger.debug("CLEANUP")
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
                logger.debug("_rollback_with_context: EXCEPT")
                if not session.session.is_active:
                    session.session.rollback()
                raise

    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        context = super(SQLAlchemyTestCase, self).assertRaises(excClass)
        if callableObj is None:
            return self._rollback_with_context(context)
        with self._rollback_with_context(context):
            callableObj(*args, **kwargs)

    def assertRaisesRegexp(self, expected_exception, expected_regexp,
                           callable_obj=None, *args, **kwargs):
        context = super(SQLAlchemyTestCase, self).assertRaisesRegexp(
            expected_exception, expected_regexp)
        if callable_obj is None:
            return self._rollback_with_context(context)
        with self._rollback_with_context(context):
            callable_obj(*args, **kwargs)

    @contextmanager
    def assertUniqueViolation(self, message):
        pattern = 'duplicate key value violates unique constraint ".+_key"'
        with self.assertRaisesRegexp(IntegrityError, pattern, msg=message) as cm:
            yield cm


class FixtureDataTestBase(SQLAlchemyTestCase, DataTestCase, unittest.TestCase):
    """A TestCase baseclass that handles database fixtures.

    You only need to define a `datasets` class member with a list of
    the fixture DataSets. The type of the fixture element will be taken
    from the name of the DataSet class. It needs "Data" as suffix. So if
    you want to provide fixtures for the User model the name of the DataSet
    has to be "UserData". See also test_property.py for an example.

    If you overwrite the `setUp` or `tearDown` methods don't forget
    to call super at the beginning or end of your implementation.

    The multiple inheritance is necessary, because the definition of
    DataTestCase is broken. It does not inherit from unittest.TestCase and it
    does not call super() in its setUp and tearDown methods. To get the MRO
    right, we have to resort to this.
    """
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.fixture = SQLAlchemyFixture(
            env=_all, style=NamedDataStyle(),
            engine=connection
        )

    def cleanup(self):
        """Override of SQLAlchemyTestCase.cleanup"""
        self.data.teardown()
        super(FixtureDataTestBase, self).cleanup()


class DialectSpecificTestCase(FixtureDataTestBase):
    """
    This is a database test that will only run on a specific SQLAlchemy dialect.
    """
    dialect = None

    def setUp(self):
        global connection
        if connection is None:
            raise AssertionError("A database connection should already have "
                                 "been initialized with setupClass or "
                                 "module/package-level setup function.")
        if connection.dialect.name != self.dialect:
            self.skipTest("This test runs only on the '{}' dialect"
                          .format(self.dialect))
        super(DialectSpecificTestCase, self).setUp()


class PostgreSQLTestCase(DialectSpecificTestCase):
    dialect = 'postgresql'


class SQLiteTestCase(DialectSpecificTestCase):
    dialect = 'sqlite'


class FactoryDataTestBase(SQLAlchemyTestCase):
    session = session.session

    def setUp(self):
        super().setUp()
        logging.getLogger('factory').setLevel(logging.INFO)
        with self.session.begin(subtransactions=True):
            self.create_factories()

    @staticmethod
    def create_factories():
        pass


class FactoryWithConfigDataTestBase(FactoryDataTestBase):
    def create_factories(self):
        self.config = ConfigFactory.create()


class FrontendDataTestBase(testing.TestCase):
    """A TestCase baseclass that handles frontend tests.

    Like the FixtureDataTestBase you have to define a data set.
    If you want a user to be logged in than you have to overwrite the 'setUp'
    method and set self.login and self.password with a user login and password.
    Do not forget to call the setUp method from the super class.

    You have to provide an user in the fixtures with the needed properties.
    """
    login = None
    password = None

    _argument_creator_map = {
        IntegerConverter: lambda c: 1,
        UnicodeConverter: lambda c: u"test",
    }
    _default_argument_creator = lambda c: u"default"

    def _login(self, login, password):
        self.client.post(url_for("login.login"), follow_redirects=True,
                         data={'login': login, 'password': password})

    def tearDown(self):
        self.client.get("/logout")
        super(FrontendDataTestBase, self).tearDown()

    def setUp(self):
        super(FrontendDataTestBase, self).setUp()
        self._login(login=self.login, password=self.password)

    def create_app(self):
        """
        Create your Flask app here, with any
        configuration you need
        """

        from web import make_app
        app = make_app()

        app.testing = True
        app.debug = True

        # Disable the CSRF in testing mode
        app.config["WTF_CSRF_ENABLED"] = False
        app.config["SECRET_KEY"] = ''.join(random.choice(string.ascii_letters)
                                           for _ in range(20))

        return app

    def blueprint_urls(self, app, blueprint_name):
        rules = [rule for rule in app.url_map.iter_rules()
                 if rule.endpoint.startswith(blueprint_name + '.')]
        url_adapter = _request_ctx_stack.top.url_adapter

        return list(map(partial(self._build_rule, url_adapter), rules))

    def _build_rule(self, url_adapter, rule):
        converters = rule._converters
        try:
            values = {
                k: self._argument_creator_map.get(
                    type(v), self._default_argument_creator
                )(v) for k, v in converters.items()}
        except KeyError as e:
            raise AssertionError("Cannot create mock argument for {}"
                                 .format(e.args[0]))
        return url_adapter.build(rule.endpoint, values, 'GET')

    def assert_template_get_request(self, endpoint, template):
        response = self.client.get(endpoint)
        self.assert200(response)
        if template:
            self.assertTemplateUsed(name=template)
        return response

    def assert_response_code(self, endpoint, code, method='get', **kwargs):
        callback_map = {
            'get': self.client.get,
            'post': self.client.post
        }
        try:
            callback = callback_map[method]
        except KeyError:
            raise ValueError("{} is not a valid method. choose from {}"
                             .format(method, list(callback_map.keys())))
        return self._assert_response_code(response=callback(endpoint, **kwargs),
                                          code=code)

    def _assert_response_code(self, response, code):
        try:
            self.assertStatus(response, code)
        except self.failureException as e:
            # raise self.failureException("{}".format(type(response).__mro__))
            exception = self.failureException("While accessing {}: {}"
                                              .format(response.location, e))
            raise self.failureException(exception).with_traceback(sys.exc_info()[2])

        return response

    def assert_access_allowed(self, endpoint):
        return self.assert_response_code(endpoint, 200)

    def assert_access_forbidden(self, endpoint):
        return self.assert_response_code(endpoint, 403)

    def assert_message_substr_flashed(self, substring, category='message'):
        for message, _category in self.flashed_messages:
            if substring in message and category == _category:
                return message

        raise AssertionError("No message with substring '{}' in category '{}' "
                             "has been flashed"
                             .format(substring, category))

    @property
    def user_id(self):
        return _all.User.q.filter_by(login=self.login).one().id


class FrontendWithAdminTestBase(FrontendDataTestBase, FactoryDataTestBase):
    def create_factories(self):
        self.login = 'hans-der-nette-admin'
        self.password = 'This is 1 strong testpassword!!'
        self.admin = UserFactory(login=self.login, password=self.password)
        admin_group = AdminPropertyGroupFactory()
        MembershipFactory.create(user=self.admin, group=admin_group)
        self.config = ConfigFactory()


class InvalidateHadesLogsMixin(testing.TestCase):
    """Mixin Class forcing a disabled `hades_logs` extensions

    This mixin class hooks into :meth:`create_app` and invalidates a
    possibly configured `hades_logs` extension.  Useful if the default
    is :py:cls:`DummyHadesLogs`.
    """
    def create_app(self):
        app = super().create_app()
        # invalidate already configured hades_logs
        if 'hades_logs' in app.extensions:
            app.extensions.pop('hades_logs')
        return app


@contextmanager
def with_debug(channel="fixture.loadable", **kw):
    start_debug(channel, **kw)
    yield
    stop_debug(channel)
