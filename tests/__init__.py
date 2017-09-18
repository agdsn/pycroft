# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import SingletonThreadPool
import sys
from werkzeug.routing import IntegerConverter, UnicodeConverter
from pycroft.model import session
from pycroft.model import _all, drop_db_model, create_db_model


engine = None
connection = None
_setup_stack = 0


def setup():
    global engine, connection, _setup_stack
    _setup_stack += 1
    if _setup_stack > 1:
        return
    try:
        uri = os.environ['PYCROFT_DB_URI']
    except KeyError:
        raise RuntimeError("Environment variable PYCROFT_DB_URI must be "
                           "set to an SQLalchemy connection string.")
    engine = create_engine(uri, poolclass=SingletonThreadPool)
    connection = engine.connect()
    drop_db_model(connection)
    create_db_model(connection)


def teardown():
    global engine, connection, _setup_stack
    _setup_stack -= 1
    if _setup_stack > 0:
        return
    drop_db_model(connection)
    connection.close()
    engine = None
    connection = None


class FixtureDataTestBase(DataTestCase, unittest.TestCase):
    """A TestCase baseclass that handles database fixtures.

    You only need to define a `datasets` class member with a list of
    the fixture DataSets. The type of the fixture element will be taken
    from the name of the DataSet class. It needs "Data" as suffic. So if
    you want to provide fixtures for the User model the name of the DataSet
    has to be "UserData". See also test_property.py for an example.

    If you overwrite the `tearDown` or `setUpClass` methods don't forget
    to call the ones in the superclass.
    """
    @classmethod
    def setUpClass(cls):
        setup()
        cls.fixture = SQLAlchemyFixture(
            env=_all, style=NamedDataStyle(),
            engine=connection
        )

    @classmethod
    def tearDownClass(cls):
        teardown()

    def setUp(self):
        super(FixtureDataTestBase, self).setUp()
        self.transaction = connection.begin_nested()
        s = scoped_session(sessionmaker(bind=connection))
        session.set_scoped_session(s)
        self.addCleanup(self.cleanup)

    def _rollback(self):
        # Rollback the session
        session.session.rollback()
        session.Session.remove()
        # Rollback the outer transaction to the savepoint
        self.transaction.rollback()
        self.transaction = None

    def tearDown(self):
        self._rollback()
        super(FixtureDataTestBase, self).tearDown()

    def cleanup(self):
        if self.transaction is None:
            return
        self._rollback()
        self.data.teardown()

    @contextmanager
    def _rollback_with_context(self, context):
        with context:
            try:
                yield
            except:
                # Check if the session is in “partial rollback” state
                if not session.session.is_active:
                    session.session.rollback()
                raise

    def assertRaises(self, excClass, callableObj=None, *args, **kwargs):
        context = super(FixtureDataTestBase, self).assertRaises(excClass)
        if callableObj is None:
            return self._rollback_with_context(context)
        with self._rollback_with_context(context):
            callableObj(*args, **kwargs)

    def assertRaisesRegexp(self, expected_exception, expected_regexp,
                           callable_obj=None, *args, **kwargs):
        context = super(FixtureDataTestBase, self).assertRaisesRegexp(
            expected_exception, expected_regexp)
        if callable_obj is None:
            return self._rollback_with_context(context)
        with self._rollback_with_context(context):
            callable_obj(*args, **kwargs)


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


class FrontendDataTestBase(FixtureDataTestBase, testing.TestCase):
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

    @property
    def user_id(self):
        return _all.User.q.filter_by(login=self.login).one().id


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
