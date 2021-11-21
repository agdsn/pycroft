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
from typing import cast

from flask import url_for, _request_ctx_stack
import flask_testing as testing
from sqlalchemy import inspect
from sqlalchemy.engine import Connection
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.declarative import DeferredReflection
from sqlalchemy.orm import sessionmaker, scoped_session, Session
from sqlalchemy.orm.session import close_all_sessions
from sqlalchemy.pool import SingletonThreadPool
import sys

from pycroft import Config
from tests.factories import ConfigFactory, UserFactory, AdminPropertyGroupFactory, MembershipFactory
from werkzeug.routing import IntegerConverter, UnicodeConverter
from pycroft.model import session, create_engine
from pycroft.model import _all, drop_db_model, create_db_model


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


class SQLAlchemyTestCase(unittest.TestCase):
    """Base class for test cases that require an initialized database

    Tests will executed inside a nested transaction using SAVEPOINTs before each
    test is test executed. Tests are rolled back after execution regardless of
    their outcome.
    """
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


class FactoryDataTestBase(SQLAlchemyTestCase):
    def setUp(self):
        super().setUp()
        logging.getLogger('factory').setLevel(logging.INFO)
        self.create_factories()
        self.session.flush()

    def create_factories(self):
        pass


class FactoryWithConfigDataTestBase(FactoryDataTestBase):
    def create_factories(self):
        self.config: Config = ConfigFactory.create()


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
        UnicodeConverter: lambda c: "test",
    }
    _default_argument_creator = lambda c: "default"

    def _login(self, login, password):
        self.client.post(url_for("login.login"),
                         data={'login': login, 'password': password})

    def tearDown(self):
        if hasattr(self, 'client2'):
            self.client2.get("/logout")
        super().tearDown()

    def setUp(self):
        super().setUp()
        self.client2 = self.client
        if self.login:
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

        raise AssertionError(
            f"No message with substring '{substring}' in category '{category}' has been flashed."
            f"Instead, we got:\n{self.flashed_messages}"
        )

    @property
    def user_id(self):
        return _all.User.q.filter_by(login=self.login).one().id


class FrontendWithAdminTestBase(FrontendDataTestBase, FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
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
