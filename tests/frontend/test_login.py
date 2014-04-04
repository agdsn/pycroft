#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import url_for

from tests import FrontendDataTestBase
from tests.frontend.fixtures import *


class Test_010_Anonymous(FrontendDataTestBase):
    """First test as anonymous user.
    Anonymous users should be able to access the login page and the /static/
    content, nothing else.
    """
    datasets = [UserData]

    def test_0010_access_anonymous(self):
        # Login is OK
        self.assert_response_code(url_for('login.login'), 200)

        # Fetching static content is OK
        self.assert_response_code('/static/style.css', 200)

        # Access to other pages/blueprints is NOT OK
        self.assert_response_code(url_for('finance.journals'), 302)
        self.assert_response_code(url_for('infrastructure.switches'), 302)


class Test_020_Login_Admin(FrontendDataTestBase):
    """Now log the user in and test some requests he is now allowed to do.
    """
    datasets = [MembershipData, PropertyData]

    def setUp(self):
        self.login = "admin"
        self.password = "password"
        FrontendDataTestBase.setUp(self)

    def test_0010_access_dormitories(self):
        # Admin has access to view the dormitories overview
        self.assert_response_code(url_for('dormitories.overview'), 200)

    def test_0020_access_finance(self):
        # Admin has no access to finance
        self.assert_response_code(url_for('finance.journals'), 302)


class Test_030_Login_Finance(FrontendDataTestBase):
    """Log in a user with advanced permissions.
    Here he may view the finance pages.
    """
    datasets = [MembershipData, PropertyData]

    def setUp(self):
        self.login = "finanzer"
        self.password = "password"
        FrontendDataTestBase.setUp(self)

    def test_0010_access_dormitories(self):
        self.assert_response_code(url_for('dormitories.overview'), 200)

    def test_0020_access_finance(self):
        self.assert_response_code(url_for('finance.journals'), 200)
