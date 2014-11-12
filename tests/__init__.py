# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from fixture.style import TrimmedNameStyle
from fixture import DataSet, SQLAlchemyFixture, DataTestCase
#from pycroft import model
from pycroft.model import _all, session, drop_db_model, create_db_model
from flask import url_for
from flask.ext import testing


__author__ = 'jan'


REGEX_NOT_NULL_CONSTRAINT = r"^\(IntegrityError\) (NOT NULL constraint failed:|([a-z_]*\.?[a-z_]*) may not be NULL)"


def make_fixture():
    """A helper to create a database fixture.
    """
    fixture = SQLAlchemyFixture(
            env=_all,
            style=TrimmedNameStyle(suffix="Data"),
            engine=session.session.get_engine())
    return fixture


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
        session.reinit_session()
        if session.session.get_engine() is None:
            print "session.session.get_engine() is None"
            session.session.init_engine("sqlite:///:memory:")
        print repr(session.session.get_engine())
        drop_db_model()
        create_db_model()
        cls.fixture = make_fixture()

    def tearDown(self):
        super(FixtureDataTestBase, self).tearDown()
        session.session.remove()


class FrontendDataTestBase(FixtureDataTestBase, testing.TestCase):
    """A TestCase baseclass that handles frontend tests.

    Like the FixtureDataTestBase you have to define a data set.
    If you want a user to be logged in than you have to overwrite the 'setUp'
    method and set self.login and self.password with a user login and password.
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
            if getattr(self, "login") is not None and \
                            getattr(self, "password") is not None:
                self._login(login=self.login, password=self.password)
        except AttributeError:
            self.__setattr__("login", None)
            self.__setattr__("Password", None)

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

    def assert_access_allowed(self, endpoint):
        return self.assert_response_code(endpoint, 200)

    def assert_access_forbidden(self, endpoint):
        return self.assert_response_code(endpoint, 302)
