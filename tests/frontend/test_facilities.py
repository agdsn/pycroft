# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import pytest
from sqlalchemy.orm import Session

from pycroft.model.facilities import Building, Room
from tests.factories import RoomFactory
from .assertions import TestClient


@pytest.mark.usefixtures("admin_logged_in")
class TestBuilding:
    @pytest.fixture(scope="class")
    def room(self, class_session: Session) -> Room:
        room = RoomFactory()
        class_session.flush()
        return room

    @pytest.fixture(scope="class")
    def building(self, class_session: Session, room: Room) -> Building:
        return room.building

    def test_list_buildings(self, test_client: TestClient):
        with test_client.renders_template("facilities/site_overview.html"):
            test_client.assert_url_ok("/facilities/sites/")

    def test_show_building(self, test_client: TestClient, building: Building):
        with test_client.renders_template("facilities/building_show.html"):
            test_client.assert_url_ok(f"/facilities/building/{building.id}/")

    def test_show_room(self, test_client: TestClient, room: Room):
        with test_client.renders_template("facilities/room_show.html"):
            test_client.assert_url_ok(f"/facilities/room/{room.id}")

    def test_building_levels(self, test_client: TestClient, building: Building):
        with test_client.renders_template("facilities/levels.html"):
            test_client.assert_url_ok(f"/facilities/building/{building.id}/levels/")

    def test_building_level_rooms(
        self, test_client: TestClient, building: Building, room: Room
    ):
        with test_client.renders_template("facilities/rooms.html"):
            test_client.assert_url_ok(
                f"/facilities/building/{building.id}/level/{room.level}/rooms/")

    def test_overcrowded_rooms(self, test_client: TestClient, building: Building):
        with test_client.renders_template("facilities/room_overcrowded.html"):
            test_client.assert_url_ok("/facilities/overcrowded")

    def test_per_building_overcrowded_rooms(
        self, test_client: TestClient, building: Building
    ):
        with test_client.renders_template("facilities/room_overcrowded.html"):
            test_client.assert_url_ok(f"/facilities/overcrowded/{building.id}")
