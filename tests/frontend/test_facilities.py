# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import pytest
from flask import url_for
from sqlalchemy.orm import Session

from pycroft.model.facilities import Building, Room, Site
from pycroft.model.port import PatchPort
from tests import factories as f
from tests.factories import RoomFactory
from .assertions import TestClient

pytestmark = pytest.mark.usefixtures("admin_logged_in", "session")


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


def test_root_redirect(client):
    client.assert_redirects(
        "facilities.root", expected_location=url_for("facilities.overview")
    )


class TestSitesOverview:
    def test_sites_overview_get(self, client):
        with client.renders_template("facilities/site_overview.html"):
            client.assert_ok("facilities.overview")

    def test_sites_overview_json(self, client):
        resp = client.assert_ok("facilities.overview_json")
        assert "items" in (j := resp.json)
        assert j["items"]


class TestSite:
    @pytest.fixture(scope="class")
    def site(self, class_session: Session) -> Site:
        return f.SiteFactory()

    def test_get_site(self, client, site):
        with client.renders_template("facilities/site_show.html"):
            client.assert_url_ok(url_for("facilities.site_show", site_id=site.id))

    def test_get_nonexistent_site(self, client):
        client.assert_url_response_code(
            url_for("facilities.site_show", site_id=999), code=404
        )


class TestBuilding:
    @pytest.fixture(scope="class")
    def room(self, class_session: Session) -> Room:
        room = RoomFactory()
        class_session.flush()
        return room

    @pytest.fixture(scope="class")
    def building(self, class_session: Session, room: Room) -> Building:
        return room.building

    def test_list_buildings(self, client: TestClient):
        with client.renders_template("facilities/site_overview.html"):
            client.assert_url_ok("/facilities/sites/")

    def test_show_building(self, client: TestClient, building: Building):
        with client.renders_template("facilities/building_show.html"):
            client.assert_url_ok(f"/facilities/building/{building.id}/")

    def test_show_nonexistent_building(self, client):
        client.assert_url_response_code(
            url_for("facilities.building_show", building_id=999), code=404
        )

    def test_show_room(self, client: TestClient, room: Room):
        with client.renders_template("facilities/room_show.html"):
            client.assert_url_ok(f"/facilities/room/{room.id}")

    def test_show_nonexistent_room(self, client):
        client.assert_url_response_code(
            url_for("facilities.room_show", room_id=999), code=404
        )

    def test_building_levels(self, client: TestClient, building: Building):
        with client.renders_template("facilities/levels.html"):
            client.assert_url_ok(f"/facilities/building/{building.id}/levels/")

    def test_nonexistent_building_levels(self, client):
        client.assert_url_response_code(
            url_for("facilities.building_levels", building_id=999), code=404
        )

    def test_building_level_rooms(
        self, client: TestClient, building: Building, room: Room
    ):
        with client.renders_template("facilities/rooms.html"):
            client.assert_url_ok(
                f"/facilities/building/{building.id}/level/{room.level}/rooms/"
            )

    def test_overcrowded_rooms(self, client: TestClient, building: Building):
        with client.renders_template("facilities/room_overcrowded.html"):
            client.assert_url_ok("/facilities/overcrowded")

    def test_per_building_overcrowded_rooms(
        self, client: TestClient, building: Building
    ):
        with client.renders_template("facilities/room_overcrowded.html"):
            client.assert_url_ok(f"/facilities/overcrowded/{building.id}")


class TestRoomCreate:
    @pytest.fixture(scope="session")
    def ep(self):
        return "facilities.room_create"

    @pytest.fixture(scope="class")
    def room(self, class_session: Session) -> Room:
        return f.RoomFactory()

    @pytest.fixture(scope="class")
    def building(self, class_session: Session, room) -> Building:
        return room.building

    def test_get_no_building(self, ep, client):
        with client.renders_template("generic_form.html"):
            client.assert_ok(ep)

    def test_get_wrong_id(self, ep, client, building):
        with client.flashes_message("Gebäude.*nicht gefunden", "error"):
            client.assert_url_redirects(url_for(ep, building_id=999))

    def test_get_correct_building_id(self, ep, client, building):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url_for(ep, building_id=building.id))

    def test_post_no_data(self, ep, client):
        with client.renders_template("generic_form.html"):
            client.assert_ok(ep, method="POST", data={})

    def test_post_wrong_data(self, ep, client):
        with client.renders_template("generic_form.html"):
            client.assert_ok(ep, method="POST", data={"building": "999"})

    def test_post_correct_data_same_room(self, ep, client, room):
        address = room.address
        formdata = {
            "building": room.building.id,
            "level": room.level,
            "number": room.number,
            "address_street": address.street,
            "address_number": address.number,
            "address_zip_code": address.zip_code,
            # addition, city, state, country optional
        }
        client.assert_ok(ep, method="POST", data=formdata)

    def test_post_correct_data_new_room(self, ep, client, building):
        address = f.AddressFactory.build()
        formdata = {
            "building": building.id,
            "level": 1,
            "number": 1,
            "address_street": address.street,
            "address_number": address.number,
            "address_zip_code": address.zip_code,
            # addition, city, state, country optional
        }
        with client.flashes_message("Raum.*erstellt", category="success"):
            client.assert_redirects(ep, method="POST", data=formdata)


class TestRoomEdit:
    @pytest.fixture(scope="session")
    def ep(self):
        return "facilities.room_edit"

    @pytest.fixture(scope="class")
    def room(self, class_session) -> Room:
        return f.RoomFactory()

    @pytest.fixture(scope="class")
    def other_room(self, class_session, room) -> Room:
        return f.RoomFactory(building=room.building, level=room.level)

    @pytest.fixture(scope="class")
    def url(self, room):
        return url_for("facilities.room_edit", room_id=room.id)

    @pytest.fixture(scope="class", autouse=True)
    def used_address(self, class_session, room):
        f.UserFactory(address=room.address, room=room)

    def test_get_no_room(self, ep, client):
        with client.flashes_message("Raum.*nicht gefunden", "error"):
            client.assert_url_redirects(url_for(ep, room_id=999))

    def test_get(self, url, client):
        with client.renders_template("generic_form.html"), client.flashes_message(
            "Adresse des Raums teilen", category="info"
        ):
            client.assert_url_ok(url)

    def test_post_no_data(self, url, client):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url, method="POST", data={})

    def test_post_wrong_data(self, url, client):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url, method="POST", data={"building": "999"})

    def test_post_correct_data(self, url, client, room):
        address = f.AddressFactory.build()
        formdata = {
            "building": room.building.id,
            "level": room.level,
            "number": room.number,
            "address_street": address.street,
            "address_number": address.number,
            "address_zip_code": address.zip_code,
            "address_addition": address.addition,
            "address_city": address.city,
            "address_country": address.country,
        }
        with client.flashes_message("erfolgreich bearbeitet", category="success"):
            client.assert_url_redirects(url, method="POST", data=formdata)

    def test_post_correct_data_ambiguous_name(self, url, client, room, other_room):
        address = room.address
        formdata = {
            "building": room.building.id,
            "level": room.level,
            "number": other_room.number,
            "address_street": address.street,
            "address_number": address.number,
            "address_zip_code": address.zip_code,
        }
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url, method="POST", data=formdata)


class TestBuildingLevelRooms:
    @pytest.fixture(scope="class")
    def ep(self) -> str:
        return "facilities.building_level_rooms_json"

    @pytest.fixture(scope="class", autouse=True)
    def building(self, class_session) -> Building:
        return f.BuildingFactory()

    @pytest.fixture(scope="class", autouse=True)
    def inhabited_room(self, class_session, building) -> Room:
        room = f.RoomFactory(level=1, building=building)
        group = f.MemberPropertyGroupFactory()
        f.UserFactory(room=room, with_membership=True, membership__group=group)
        f.UserFactory(room=room)
        return room

    @pytest.fixture(scope="class", autouse=True)
    def uninhabited_room(self, building):
        return f.RoomFactory(level=1, building=building)

    def test_all_users(self, client, ep, building):
        url = url_for(ep, building_id=building.id, level=1, all_users=1)
        resp = client.assert_url_ok(url)
        assert "items" in (j := resp.json)
        assert len(j["items"]) == 2
        assert {len(r["inhabitants"]) for r in j["items"]} == {0, 2}

    def test_not_all_users(self, client, ep, building):
        url = url_for(ep, building_id=building.id, level=1)
        resp = client.assert_url_ok(url)
        assert "items" in (j := resp.json)
        assert len(j["items"]) == 2
        assert {len(r["inhabitants"]) for r in j["items"]} == {0, 1}


class TestPatchPortCreate:
    @pytest.fixture(scope="class")
    def ep(self) -> str:
        return "facilities.patch_port_create"

    @pytest.fixture(scope="class")
    def room(self, class_session) -> Room:
        return f.RoomFactory()

    @pytest.fixture(scope="class")
    def switch_room(self, class_session) -> Room:
        switch = f.SwitchFactory()
        return switch.host.room

    @pytest.fixture(scope="class")
    def patch_port(self, switch_room) -> PatchPort:
        return f.PatchPortFactory(switch_room=switch_room)

    @pytest.fixture(scope="class")
    def url(self, ep, switch_room) -> str:
        """Endpoint URL for the patched room, where a POST makes sense"""
        return url_for(ep, switch_room_id=switch_room.id)

    def test_get_nonexistent_room(self, client, ep):
        with client.flashes_message("Raum.*nicht gefunden", category="error"):
            client.assert_url_redirects(url_for(ep, switch_room_id=999))

    def test_get_non_switch_room(self, client, ep, room):
        with client.flashes_message("kein Switchraum", category="error"):
            client.assert_url_redirects(url_for(ep, switch_room_id=room.id))

    def test_get_switch_room(self, client, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url)

    def test_post_no_data(self, client, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url, method="POST", data={})

    def test_post_wrong_data(self, client, url):
        data = {"switch": "999"}
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url, method="POST", data=data)

    def test_post_existing_patch_port(self, client, url, switch_room, room, patch_port):
        data = {
            "name": patch_port.name,
            "switch_room": switch_room.id,
            "building": room.building.id,
            "level": room.level,
            "room_number": room.number,
        }
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url, method="POST", data=data)

    def test_post_new_patch_port(self, client, url, patch_port, switch_room, room):
        data = {
            "name": f"{patch_port.name}-2",
            "switch_room": switch_room.id,
            "building": room.building.id,
            "level": room.level,
            "room_number": room.number,
        }
        with client.flashes_message("erfolgreich erstellt", category="success"):
            client.assert_url_redirects(url, method="POST", data=data)
