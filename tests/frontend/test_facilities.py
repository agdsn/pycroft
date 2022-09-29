# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import pytest
from flask.testing import FlaskClient

from tests.factories import RoomFactory


class TestBuilding:
    @pytest.fixture(scope="class")
    def room(self, class_session):
        room = RoomFactory()
        class_session.flush()
        return room

    @pytest.fixture(scope="class")
    def building(self, class_session, room):
        return room.building

    @pytest.fixture(scope="class", autouse=True)
    def login(self, processor):
        pass

    @staticmethod
    def assert_template_used(rendered_templates, template_name: str) -> None:
        rendered_template_names = [t.name for (t, _ctx) in rendered_templates]
        assert (
            rendered_template_names == [template_name]
        ), f"template {template_name!r} was not rendered"

    def assert_template_get_request(
        self, client: FlaskClient, rendered_templates, endpoint: str, template: str
    ):
        response = client.get(endpoint)
        assert response.status_code == 200
        if template:
            self.assert_template_used(rendered_templates, template)
        return response

    def test_list_buildings(self, test_client, rendered_templates):
        self.assert_template_get_request(
            test_client,
            rendered_templates,
            "/facilities/sites/",
            "facilities/site_overview.html",
        )

    def test_show_building(self, test_client, rendered_templates, building):
        self.assert_template_get_request(
            test_client,
            rendered_templates,
            f"/facilities/building/{building.id}/",
            "facilities/building_show.html",
        )

    def test_show_room(self, test_client, rendered_templates, room):
        self.assert_template_get_request(
            test_client,
            rendered_templates,
            f"/facilities/room/{room.id}",
            "facilities/room_show.html",
        )

    def test_building_levels(self, test_client, rendered_templates, building):
        self.assert_template_get_request(
            test_client,
            rendered_templates,
            f"/facilities/building/{building.id}/levels/",
            "facilities/levels.html",
        )

    def test_building_level_rooms(
        self, test_client, rendered_templates, building, room
    ):
        self.assert_template_get_request(
            test_client,
            rendered_templates,
            f"/facilities/building/{building.id}/level/{room.level}/rooms/",
            "facilities/rooms.html",
        )

    def test_overcrowded_rooms(self, test_client, rendered_templates, building):
        self.assert_template_get_request(
            test_client,
            rendered_templates,
            "/facilities/overcrowded",
            "facilities/room_overcrowded.html",
        )

    def test_per_building_overcrowded_rooms(
        self, test_client, rendered_templates, building
    ):
        self.assert_template_get_request(
            test_client,
            rendered_templates,
            f"/facilities/overcrowded/{building.id}",
            "facilities/room_overcrowded.html",
        )
