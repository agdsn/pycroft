# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask import url_for
from pycroft.model.facilities import Dormitory, Room

from tests import FrontendDataTestBase
from tests.fixtures.dummy.dormitory import DormitoryData, RoomData
from tests.fixtures.permissions import UserData, PropertyData, MembershipData


class Test_010_Dormitory(FrontendDataTestBase):
    datasets = (DormitoryData, MembershipData, PropertyData, RoomData, UserData)
    login = UserData.user1_admin.login
    password = UserData.user1_admin.password

    def setUp(self):
        super(Test_010_Dormitory, self).setUp()
        self.dormitory = Dormitory.q.filter_by(
            street=DormitoryData.dummy_house1.street,
            number=DormitoryData.dummy_house1.number).one()
        self.room = Room.q.filter_by(dormitory=self.dormitory,
                                     number=RoomData.dummy_room1.number,
                                     level=RoomData.dummy_room1.level).one()

    def test_0010_list_dormitories(self):
        self.assert_template_get_request("/dormitories/",
                                         "dormitories/overview.html")

    def test_0020_show_dormitory(self):
        self.assert_template_get_request(
            "/dormitories/show/{}".format(self.dormitory.id),
            "dormitories/dormitory_show.html")

    def test_0040_show_room(self):
        self.assert_template_get_request(
            "/dormitories/room/show/{}".format(self.room.id),
            "dormitories/room_show.html")

    def test_0070_dormitory_levels(self):
        self.assert_template_get_request(
            "/dormitories/levels/{}".format(self.dormitory.id),
            "dormitories/levels.html")

    def test_0080_dormitory_level_rooms(self):
        self.assert_template_get_request(
            "/dormitories/levels/{}/rooms/{}".format(
                self.dormitory.id, self.room.level),
            "dormitories/rooms.html")
