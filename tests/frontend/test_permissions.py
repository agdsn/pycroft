# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask import url_for, current_app

from tests import FrontendDataTestBase
from tests.fixtures.permissions import UserData, MembershipData, PropertyData


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
        self.assert_response_code(url_for('static', filename='style.css'), 200)

        # Access to other pages/blueprints is NOT OK
        self.assert_response_code(url_for('finance.bank_accounts_list'), 302)
        self.assert_response_code(url_for('infrastructure.switches'), 302)


class Test_020_Permissions_Admin(FrontendDataTestBase):
    """Test permissions for admin usergroup.
    """
    datasets = [MembershipData, PropertyData]

    def setUp(self):
        self.login = UserData.user1_admin.login
        self.password = UserData.user1_admin.password
        FrontendDataTestBase.setUp(self)

    def test_0010_access_buildings(self):
        # Admin has access to view the facilities overview
        self.assert_response_code(url_for('facilities.overview'), 200)

    def test_0020_access_finance(self):
        # Admin has no access to finance
        self.assert_access_forbidden(url_for('finance.bank_accounts_list'))


class Test_030_Permissions_Finance(FrontendDataTestBase):
    """Test permissions for finance usergroup (advanced).
    """
    datasets = [MembershipData, PropertyData]

    def setUp(self):
        self.login = UserData.user2_finance.login
        self.password = UserData.user2_finance.password
        FrontendDataTestBase.setUp(self)

    def test_0010_access_buildings(self):
        self.assert_response_code(url_for('facilities.overview'), 200)

    def test_0020_access_finance(self):
        self.assert_response_code(url_for('finance.bank_accounts_list'), 200)


class Test_040_Permissions_User(FrontendDataTestBase):
    """Test permissions as a user without any membership
    """
    datasets = [UserData, MembershipData, PropertyData]

    def setUp(self):
        self.login = UserData.user3_user.login
        self.password = UserData.user3_user.password
        FrontendDataTestBase.setUp(self)

    def test_0010_access_user(self):
        for url in self.blueprint_urls(current_app, 'user'):
            self.assert_access_forbidden(url)

    def test_0020_access_finance(self):
        for url in self.blueprint_urls(current_app, 'finance'):
            self.assert_access_forbidden(url)

    def test_0030_access_buildings(self):
        for url in self.blueprint_urls(current_app, 'facilities'):
            self.assert_access_forbidden(url)

    def test_0040_access_infrastructure(self):
        for url in self.blueprint_urls(current_app, 'infrastructure'):
            self.assert_access_forbidden(url)

    def test_0050_access_properties(self):
        for url in self.blueprint_urls(current_app, 'properties'):
            self.assert_access_forbidden(url)

    def test_0060_access_login(self):
        # Login see Test_010_Anonymous
        #TODO assert client response by text or better, not code
        self.assert_response_code(url_for('login.logout'), 302)
