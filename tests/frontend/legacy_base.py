#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import random
import string
import sys
import warnings

import flask_testing as testing
from flask import url_for

from pycroft.model import _all
from tests.factories import UserFactory, AdminPropertyGroupFactory, \
    MembershipFactory, ConfigFactory
from tests.legacy_base import FactoryDataTestBase


class FrontendDataTestBase(testing.TestCase):
    """A TestCase baseclass that handles frontend tests.

    Like the FixtureDataTestBase you have to define a data set.
    If you want a user to be logged in than you have to overwrite the 'setUp'
    method and set self.login and self.password with a user login and password.
    Do not forget to call the setUp method from the super class.

    You have to provide an user in the fixtures with the needed properties.
    """
    warnings.warn('Use pytest with the `session` fixture instead', DeprecationWarning)
    login = None
    password = None

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
            raise ValueError(
                f"{method} is not a valid method. choose from {list(callback_map.keys())}"
            )
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
    warnings.warn('Use pytest with the `session` fixture instead', DeprecationWarning)
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
    is :class:`DummyHadesLogs`.
    """
    def __init__(self, *a, **kw):
        warnings.warn('Use pytest with the `session` fixture instead', DeprecationWarning)
        super().__init__(*a, **kw)

    def create_app(self):
        app = super().create_app()
        # invalidate already configured hades_logs
        if 'hades_logs' in app.extensions:
            app.extensions.pop('hades_logs')
        return app
