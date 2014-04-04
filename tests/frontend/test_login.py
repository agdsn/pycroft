#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import url_for

from tests import FrontendDataTestBase
from tests.frontend.fixtures.login_fixtures import DormitoryData, RoomData, UserData, \
    MembershipData, PropertyData, PropertyGroupData


class Test_010_Anonymous(FrontendDataTestBase):
    """First test as anonymous user.
    Anonymous users should be able to access the login page and the /static/
    content, nothing else.
    """
    datasets = [DormitoryData, RoomData, UserData]

    def test_0010_access_forbidden(self):
        # Login is OK
        self.assert_response_code(url_for('login.login'), 200)

        # Fetching static content is OK
        self.assert_response_code('/static/style.css', 200)

        # Access to other pages/blueprints is NOT OK
        self.assert_response_code(url_for('finance.journals'), 302)
        self.assert_response_code(url_for('infrastructure.switches'), 302)


class Test_020_Login(FrontendDataTestBase):
    """Now log the user in and test some requests he is now allowed to do.
    This test can be buggy, if
    """
    datasets = [DormitoryData, RoomData, UserData, MembershipData, PropertyData, PropertyGroupData]

    def setUp(self):
        self.login = "test"
        self.password = "password"
        #super(Test_020_Login, self).setUp()
        FrontendDataTestBase.setUp(self)

    def test_0010_access_dormitories(self):
        self.assert_response_code(url_for('dormitories.overview'), 200)

    def test_0020_finance(self):
        self.assert_response_code(url_for('finance.journals'), 200)
