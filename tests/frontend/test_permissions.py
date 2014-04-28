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


class Test_020_Permissions_Admin(FrontendDataTestBase):
    """Test permissions for admin usergroup.
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


class Test_030_Permissions_Finance(FrontendDataTestBase):
    """Test permissions for finance usergroup (advanced).
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


class Test_040_Permissions_User(FrontendDataTestBase):
    """Test permissions as a user without any membership
    """
    datasets = [UserData, MembershipData, PropertyData]

    def setUp(self):
        self.login = "user"
        self.password = "password"
        FrontendDataTestBase.setUp(self)

    def test_0010_access_user(self):
        for url in (
            url_for('user.create'),
            url_for('user.move', user_id=1),
            url_for('user.user_show', user_id=1),
            url_for('user.add_membership', user_id=1),
            url_for('user.end_membership', membership_id=1),
            url_for('user.edit_membership', membership_id=1),
            url_for('user.edit_name', user_id=1),
            url_for('user.edit_email', user_id=1),
            url_for('user.block', user_id=1),
            url_for('user.move_out', user_id=1),
            url_for('user.change_mac', user_net_device_id=1),
            url_for('user.move_out_tmp', user_id=1),
            url_for('user.is_back', user_id=1),
            url_for('user.json_levels'),
            url_for('user.json_rooms'),
            url_for('user.json_trafficdata', user_id=1),
            url_for('user.search')
        ):
            self.assert_access_forbidden(url)

    def test_0020_access_finance(self):
        for url in (
            url_for('finance.journals'),
            url_for('finance.journal_import'),
            url_for('finance.journal_create'),
            url_for('finance.journalentry_edit', entryid=1),
            url_for('finance.accounts'),
            url_for('finance.accounts_create'),
            url_for('finance.show_account', account_id=1),
            url_for('finance.show_transaction', transaction_id=1),
            url_for('finance.semester_list'),
            url_for('finance.semester_create'),
            url_for('finance.json_search_accounts', search_str="Teststring")
        ):
            self.assert_access_forbidden(url)

    def test_0030_access_dormitories(self):
        for url in (
            url_for('dormitories.overview'),
        ):
            self.assert_access_allowed(url)

        for url in (
            url_for('dormitories.dormitory_show', dormitory_id=1),
            url_for('dormitories.dormitory_create'),
            url_for('dormitories.room_delete', room_id=1),
            url_for('dormitories.room_show', room_id=1),
            url_for('dormitories.room_create'),
            url_for('dormitories.dormitory_levels', dormitory_id=1),
            url_for('dormitories.dormitory_level_rooms', dormitory_id=1, level=1)
        ):
            self.assert_access_forbidden(url)

    def test_0040_access_infrastructure(self):
        for url in (
            url_for('infrastructure.subnets'),
            url_for('infrastructure.switches'),
            url_for('infrastructure.vlans'),
            url_for('infrastructure.record_delete', user_id=1, alias_id=1),
            url_for('infrastructure.record_edit', user_id=1, alias_id=1),
            url_for('infrastructure.arecord_edit', user_id=1, alias_id=1),
            url_for('infrastructure.aaaarecord_edit', user_id=1, alias_id=1),
            url_for('infrastructure.cnamerecord_edit', user_id=1, alias_id=1),
            url_for('infrastructure.mxrecord_edit', user_id=1, alias_id=1),
            url_for('infrastructure.nsrecord_edit', user_id=1, alias_id=1),
            url_for('infrastructure.srvrecord_edit', user_id=1, alias_id=1),
            url_for('infrastructure.record_create', user_id=1, host_id=1),
            url_for('infrastructure.arecord_create', user_id=1, host_id=1),
            url_for('infrastructure.aaaarecord_create', user_id=1, host_id=1),
            url_for('infrastructure.cnamerecord_create', user_id=1, host_id=1),
            url_for('infrastructure.mxrecord_create', user_id=1, host_id=1),
            url_for('infrastructure.nsrecord_create', user_id=1, host_id=1),
            url_for('infrastructure.srvrecord_create', user_id=1, host_id=1),
            url_for('infrastructure.switch_show', switch_id=1),
            url_for('infrastructure.switch_port_create', switch_id=1)
        ):
            self.assert_access_forbidden(url)

    def test_0050_access_properties(self):
        for url in (
            url_for('properties.traffic_groups'),
            url_for('properties.traffic_group_create'),
            url_for('properties.property_groups'),
            url_for('properties.property_group_create'),
            url_for('properties.property_group_add_property', group_id=1, property_name="Testproperty"),
            url_for('properties.property_group_delete_property', group_id=1, property_name="Testproperty"),
            url_for('properties.property_group_delete', group_id=1)
        ):
            self.assert_access_forbidden(url)

    def test_0060_access_login(self):
        # Login see Test_010_Anonymous
        #TODO assert client response by text or better, not code
        self.assert_response_code(url_for('login.logout'), 302)
