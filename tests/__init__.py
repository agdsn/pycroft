# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture.style import TrimmedNameStyle
from fixture import DataSet, SQLAlchemyFixture, DataTestCase
from pycroft.model import session, _all
from pycroft.model import drop_db_model, create_db_model
from flask import url_for, request
from flask.ext import testing
from web import make_app

from tests.unittest26_compat import OldPythonTestCase

__author__ = 'jan'

REGEX_NOT_NULL_CONSTRAINT = r"^\(IntegrityError\) NOT NULL constraint failed:"


def make_fixture():
    """A helper to create a database fixture.
    """
    fixture = SQLAlchemyFixture(
            env=_all,
            style=TrimmedNameStyle(suffix="Data"),
            engine=session.session.get_engine() )
    return fixture


class FixtureDataTestBase(DataTestCase, OldPythonTestCase):
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
        session.reinit_session("sqlite://")
        drop_db_model()
        create_db_model()
        cls.fixture = make_fixture()

    def tearDown(self):
        super(FixtureDataTestBase, self).tearDown()
        session.session.remove()


class FrontendDataTestBase(FixtureDataTestBase, testing.TestCase):
    """A TestCase baseclass that handeles frontend tests.

    Like the FixtureDataTestBase you have to define a dataset.
    If you want a user to be logged in than you have to overwrite the 'setUp' method
    and set self.login and self.password with a user login and password.
    Do not forget to call the setUp method from the super class.

    You have to provide an user in the fixtures with the needed properties.
    """
    def _login(self, login, password):
        self.client.post(url_for("login.login"), data=dict(
            login=login,
            password=password),
            follow_redirects=True)

    def tearDown(self):
        self.client.get("/logout")
        super(FrontendDataTestBase, self).tearDown()

    def setUp(self):
        super(FrontendDataTestBase, self).setUp()
        try:
            if getattr(self, "login") is not None and getattr(self, "password") is not None:
                self._login(login=self.login, password=self.password)
        except AttributeError:
            self.__setattr__("login", None)
            self.__setattr__("Password", None)

    def create_app(self):
        """
        Create your Flask app here, with any
        configuration you need
        """
        app = make_app()
        app.testing = True

        # Disable the CSRF in testing mode
        app.config["WTF_CSRF_ENABLED"] = False

        return app

    def assert_template_get_request(self, endpoint, template):
        response = self.client.get(endpoint)
        self.assert200(response)
        if template:
            self.assertTemplateUsed(name=template)
        return response

    def assert_response_code(self, endpoint, code):
        response = self.client.get(endpoint)
        self.assertStatus(response, code)
        return response
