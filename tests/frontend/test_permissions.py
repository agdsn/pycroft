# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask import url_for, current_app
from jinja2.runtime import Context

from tests import FrontendDataTestBase, FixtureDataTestBase
from tests.fixtures.permissions import UserData, MembershipData, PropertyData
from tests.fixtures.config import ConfigData
from web.template_filters import require


class PermissionsTestBase(FrontendDataTestBase, FixtureDataTestBase):
    datasets = [MembershipData, PropertyData, ConfigData]


class Test_010_Anonymous(FrontendDataTestBase, FixtureDataTestBase):
    """First test as anonymous user.
    Anonymous users should be able to access the login page and the /static/
    content, nothing else.
    """
    datasets = [UserData]

    def test_0010_access_anonymous(self):
        # Login is OK
        self.assert_response_code(url_for('login.login'), 200)

        ctx = Context(self.app.jinja_env, None, "pseudo", {})
        # Fetching static content is OK
        self.assert_response_code(require(ctx, 'main.css'), 200)

        # Access to other pages/blueprints is NOT OK
        self.assert_response_code(url_for('finance.bank_accounts_list'), 302)
        self.assert_response_code(url_for('infrastructure.switches'), 302)


class Test_020_Permissions_Admin(PermissionsTestBase):
    """Test permissions for admin usergroup.
    """

    def setUp(self):
        self.login = UserData.user1_admin.login
        self.password = UserData.user1_admin.password
        super().setUp()

    def test_0010_access_buildings(self):
        # Admin has access to view the facilities overview
        self.assert_response_code(url_for('facilities.overview'), 200)

    def test_0020_access_finance(self):
        # Admin has no access to finance
        self.assert_access_forbidden(url_for('finance.bank_accounts_list'))


class Test_030_Permissions_Finance(FrontendDataTestBase, FixtureDataTestBase):
    """Test permissions for finance usergroup (advanced).
    """
    datasets = [MembershipData, PropertyData, ConfigData]

    def setUp(self):
        self.login = UserData.user2_finance.login
        self.password = UserData.user2_finance.password
        super().setUp()

    def test_0010_access_buildings(self):
        self.assert_response_code(url_for('facilities.overview'), 200)

    def test_0020_access_finance(self):
        self.assert_response_code(url_for('finance.bank_accounts_list'), 200)


class Test_040_Permissions_User(PermissionsTestBase):
    """Test permissions as a user without any membership
    """

    def setUp(self):
        self.login = UserData.user3_user.login
        self.password = UserData.user3_user.password
        super().setUp()

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
