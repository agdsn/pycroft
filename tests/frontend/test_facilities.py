# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from tests.factories import RoomFactory, AdminPropertyGroupFactory, UserFactory
from tests.frontend.legacy_base import FrontendDataTestBase
from tests.legacy_base import FactoryWithConfigDataTestBase


class TestBuilding(FrontendDataTestBase, FactoryWithConfigDataTestBase):
    login = 'shoot-the-root'
    password = 'password'

    def create_factories(self):
        super().create_factories()
        self.user = UserFactory(
            login=self.login,
            password=self.password,
            with_membership=True,
            membership__group=AdminPropertyGroupFactory.create(),
        )
        self.room = RoomFactory()
        self.building = self.room.building

    def test_list_buildings(self):
        self.assert_template_get_request("/facilities/sites/",
                                         "facilities/site_overview.html")

    def test_show_building(self):
        self.assert_template_get_request(
            f"/facilities/building/{self.building.id}/",
            "facilities/building_show.html")

    def test_show_room(self):
        self.assert_template_get_request(
            f"/facilities/room/{self.room.id}",
            "facilities/room_show.html")

    def test_building_levels(self):
        self.assert_template_get_request(
            f"/facilities/building/{self.building.id}/levels/",
            "facilities/levels.html")

    def test_building_level_rooms(self):
        self.assert_template_get_request(
            f"/facilities/building/{self.building.id}/level/{self.room.level}/rooms/",
            "facilities/rooms.html")

    def test_overcrowded_rooms(self):
        self.assert_template_get_request(
            "/facilities/overcrowded",
            "facilities/room_overcrowded.html")

    def test_per_building_overcrowded_rooms(self):
        self.assert_template_get_request(
            f"/facilities/overcrowded/{self.building.id}",
            "facilities/room_overcrowded.html")
