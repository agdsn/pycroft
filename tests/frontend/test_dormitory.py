# -*- coding: utf-8 -*-
# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from tests import FrontendDataTestBase
from tests.frontend.fixtures.dormitory_fixtures import DormitoryData, RoomData, UserData

__author__ = 'Florian Österreich'


class Test_010_Dormitory(FrontendDataTestBase):
    datasets = [DormitoryData, RoomData, UserData]

    def setUp(self):
        self.login = "test"
        self.password = "password"
        super(Test_010_Dormitory, self).setUp()

    def test_0010_list_dormitories(self):
        self.assert_template_get_request("/dormitories/", "dormitories/overview.html")
