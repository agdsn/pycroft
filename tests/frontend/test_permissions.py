#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

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
        self.assert_access_forbidden(url_for('user.create'))
        self.assert_access_forbidden(url_for('user.move', user_id=1))
        self.assert_access_forbidden(url_for('user.user_show', user_id=1))
        self.assert_access_forbidden(url_for('user.add_membership', user_id=1))
        self.assert_access_forbidden(url_for('user.end_membership', membership_id=1))
        self.assert_access_forbidden(url_for('user.edit_membership', membership_id=1))
        self.assert_access_forbidden(url_for('user.edit_name', user_id=1))
        self.assert_access_forbidden(url_for('user.edit_email', user_id=1))
        self.assert_access_forbidden(url_for('user.block', user_id=1))
        self.assert_access_forbidden(url_for('user.move_out', user_id=1))
        self.assert_access_forbidden(url_for('user.change_mac', user_net_device_id=1))
        self.assert_access_forbidden(url_for('user.move_out_tmp', user_id=1))
        self.assert_access_forbidden(url_for('user.is_back', user_id=1))
        self.assert_access_forbidden(url_for('user.json_levels'))
        self.assert_access_forbidden(url_for('user.json_rooms'))
        self.assert_access_forbidden(url_for('user.json_trafficdata', user_id=1))
        self.assert_access_forbidden(url_for('user.search'))

    def test_0020_access_finance(self):
        self.assert_access_forbidden(url_for('finance.journals'))
        self.assert_access_forbidden(url_for('finance.journal_import'))
        self.assert_access_forbidden(url_for('finance.journal_create'))
        self.assert_access_forbidden(url_for('finance.journalentry_edit', entryid=1))
        self.assert_access_forbidden(url_for('finance.accounts'))
        self.assert_access_forbidden(url_for('finance.accounts_create'))
        self.assert_access_forbidden(url_for('finance.transactions'))
        self.assert_access_forbidden(url_for('finance.semester_list'))
        self.assert_access_forbidden(url_for('finance.semester_create'))
        self.assert_access_forbidden(url_for('finance.json_search_accounts', search_str="Teststring"))

    def test_0030_access_dormitories(self):
        self.assert_access_allowed(url_for('dormitories.overview'))

        self.assert_access_forbidden(url_for('dormitories.dormitory_show', dormitory_id=1))
        self.assert_access_forbidden(url_for('dormitories.dormitory_create'))
        self.assert_access_forbidden(url_for('dormitories.room_delete', room_id=1))
        self.assert_access_forbidden(url_for('dormitories.room_show', room_id=1))
        self.assert_access_forbidden(url_for('dormitories.room_create'))
        self.assert_access_forbidden(url_for('dormitories.dormitory_levels', dormitory_id=1))
        self.assert_access_forbidden(url_for('dormitories.dormitory_level_rooms', dormitory_id=1, level=1))

    def test_0040_access_infrastructure(self):
        self.assert_access_forbidden(url_for('infrastructure.subnets'))
        self.assert_access_forbidden(url_for('infrastructure.switches'))
        self.assert_access_forbidden(url_for('infrastructure.vlans'))
        self.assert_access_forbidden(url_for('infrastructure.record_delete', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.record_edit', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.arecord_edit', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.aaaarecord_edit', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.cnamerecord_edit', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.mxrecord_edit', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.nsrecord_edit', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.srvrecord_edit', user_id=1, alias_id=1))
        self.assert_access_forbidden(url_for('infrastructure.record_create', user_id=1, host_id=1))
        self.assert_access_forbidden(url_for('infrastructure.arecord_create', user_id=1, host_id=1))
        self.assert_access_forbidden(url_for('infrastructure.aaaarecord_create', user_id=1, host_id=1))
        self.assert_access_forbidden(url_for('infrastructure.cnamerecord_create', user_id=1, host_id=1))
        self.assert_access_forbidden(url_for('infrastructure.mxrecord_create', user_id=1, host_id=1))
        self.assert_access_forbidden(url_for('infrastructure.nsrecord_create', user_id=1, host_id=1))
        self.assert_access_forbidden(url_for('infrastructure.srvrecord_create', user_id=1, host_id=1))
        self.assert_access_forbidden(url_for('infrastructure.switch_show', switch_id=1))
        self.assert_access_forbidden(url_for('infrastructure.switch_port_create', switch_id=1))

    def test_0050_access_properties(self):
        self.assert_access_forbidden(url_for('properties.traffic_groups'))
        self.assert_access_forbidden(url_for('properties.traffic_group_create'))
        self.assert_access_forbidden(url_for('properties.property_groups'))
        self.assert_access_forbidden(url_for('properties.property_group_create'))
        self.assert_access_forbidden(url_for('properties.property_group_add_property', group_id=1, property_name="Testproperty"))
        self.assert_access_forbidden(url_for('properties.property_group_delete_property', group_id=1, property_name="Testproperty"))
        self.assert_access_forbidden(url_for('properties.property_group_delete', group_id=1))

    def test_0060_access_login(self):
        # Login see Test_010_Anonymous
        #TODO assert client response by text or better, not code
        self.assert_response_code(url_for('login.logout'), 302)
