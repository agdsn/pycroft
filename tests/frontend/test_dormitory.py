# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask import url_for

from tests import FrontendDataTestBase
from tests.frontend.fixtures import *


class Test_010_Dormitory(FrontendDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, PropertyData, PropertyGroupData, MembershipData]

    def setUp(self):
        self.login = "admin"
        self.password = "password"
        super(Test_010_Dormitory, self).setUp()

    def test_0010_list_dormitories(self):
        self.assert_template_get_request("/dormitories/",
                                         "dormitories/overview.html")

    def test_0020_show_dormitory(self):
        self.assert_template_get_request(
            "/dormitories/show/{}".format(DormitoryData.dummy_house1.id),
            "dormitories/dormitory_show.html")

    def test_0040_show_room(self):
        self.assert_template_get_request(
            "/dormitories/room/show/{}".format(RoomData.dummy_room1.id),
            "dormitories/room_show.html")

    def test_0070_dormitory_levels(self):
        self.assert_template_get_request(
            "/dormitories/levels/{}".format(DormitoryData.dummy_house1.id),
            "dormitories/levels.html")

    def test_0080_dormitory_level_rooms(self):
        self.assert_template_get_request(
            "/dormitories/levels/{}/rooms/{}".format(
            DormitoryData.dummy_house1.id, RoomData.dummy_room1.level),
            "dormitories/rooms.html")
