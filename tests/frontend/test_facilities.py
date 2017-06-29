# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from flask import url_for
from pycroft.model.facilities import Building, Room

from tests import FrontendDataTestBase
from tests.fixtures.config import ConfigData
from tests.fixtures.dummy.facilities import BuildingData, RoomData
from tests.fixtures.permissions import UserData, PropertyData, MembershipData


class Test_010_Building(FrontendDataTestBase):
    datasets = (ConfigData, BuildingData, MembershipData, PropertyData,
                RoomData, UserData)
    login = UserData.user1_admin.login
    password = UserData.user1_admin.password

    def setUp(self):
        super(Test_010_Building, self).setUp()
        self.building = Building.q.filter_by(
            street=BuildingData.dummy_house1.street,
            number=BuildingData.dummy_house1.number).one()
        self.room = Room.q.filter_by(building=self.building,
                                     number=RoomData.dummy_room1.number,
                                     level=RoomData.dummy_room1.level).one()

    def test_0010_list_buildings(self):
        self.assert_template_get_request("/facilities/sites/",
                                         "facilities/site_overview.html")

    def test_0020_show_building(self):
        self.assert_template_get_request(
            "/facilities/buildings/{}/".format(self.building.id),
            "facilities/building_show.html")

    def test_0040_show_room(self):
        self.assert_template_get_request(
            "/facilities/rooms/{}".format(self.room.id),
            "facilities/room_show.html")

    def test_0070_building_levels(self):
        self.assert_template_get_request(
            "/facilities/buildings/{}/levels/".format(self.building.id),
            "facilities/levels.html")

    def test_0080_building_level_rooms(self):
        self.assert_template_get_request(
            "/facilities/buildings/{}/levels/{}/rooms/".format(
                self.building.id, self.room.level),
            "facilities/rooms.html")

    def test_overcrowded_rooms(self):
        self.assert_template_get_request(
            "/facilities/overcrowded",
            "facilities/room_overcrowded.html")
