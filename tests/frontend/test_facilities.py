# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from tests import FrontendDataTestBase, FactoryWithConfigDataTestBase, AdminPropertyGroupFactory
from tests.factories import RoomFactory
from tests.factories.user import UserWithMembershipFactory


class Test_010_Building(FrontendDataTestBase, FactoryWithConfigDataTestBase):
    login = 'shoot-the-root'
    password = 'password'

    def create_factories(self):
        super().create_factories()
        self.user = UserWithMembershipFactory(
            login=self.login,
            password=self.password,
            membership__group=AdminPropertyGroupFactory.create(),
        )
        self.room = RoomFactory()
        self.building = self.room.building

    def test_0010_list_buildings(self):
        self.assert_template_get_request("/facilities/sites/",
                                         "facilities/site_overview.html")

    def test_0020_show_building(self):
        self.assert_template_get_request(
            "/facilities/building/{}/".format(self.building.id),
            "facilities/building_show.html")

    def test_0040_show_room(self):
        self.assert_template_get_request(
            "/facilities/room/{}".format(self.room.id),
            "facilities/room_show.html")

    def test_0070_building_levels(self):
        self.assert_template_get_request(
            "/facilities/building/{}/levels/".format(self.building.id),
            "facilities/levels.html")

    def test_0080_building_level_rooms(self):
        self.assert_template_get_request(
            "/facilities/building/{}/level/{}/rooms/".format(
                self.building.id, self.room.level),
            "facilities/rooms.html")

    def test_overcrowded_rooms(self):
        self.assert_template_get_request(
            "/facilities/overcrowded",
            "facilities/room_overcrowded.html")

    def test_per_building_overcrowded_rooms(self):
        self.assert_template_get_request(
            "/facilities/overcrowded/{}".format(self.building.id),
            "facilities/room_overcrowded.html")
