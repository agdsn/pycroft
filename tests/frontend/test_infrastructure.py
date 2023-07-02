# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re
import typing as t

import pytest
from ipaddr import IPv4Network, IPv4Address
from sqlalchemy.orm import Session
from flask import url_for

from pycroft.model.facilities import Room
from pycroft.model.host import Switch, SwitchPort
from pycroft.model.net import Subnet
from pycroft.model.port import PatchPort
from tests import factories as f
from web.blueprints.infrastructure import format_address_range
from .assertions import TestClient


@pytest.fixture(scope="module")
def switch(module_session: Session) -> Switch:
    switch = f.SwitchFactory()
    module_session.flush()
    return switch


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


def test_format_empty_address_range():
    with pytest.raises(ValueError):
        format_address_range(IPv4Address("141.30.228.39"), amount=0)


@pytest.mark.usefixtures("admin_logged_in", "session")
class TestSubnets:
    @pytest.fixture(scope="class", autouse=True)
    def subnets(self, class_session: Session) -> list[Subnet]:
        return f.SubnetFactory.create_batch(3) + [
            f.SubnetFactory(reserved_addresses_bottom=1, reserved_addresses_top=5),
            f.SubnetFactory(reserved_addresses_bottom=5, reserved_addresses_top=1),
            f.SubnetFactory(address=IPv4Network("141.30.228.1/32")),
        ]

    def test_subnets(self, client):
        with client.renders_template("infrastructure/subnets_list.html"):
            client.assert_url_ok(url_for("infrastructure.subnets"))

    def test_subnets_json(self, client):
        response = client.assert_url_ok(url_for("infrastructure.subnets_json"))
        assert "items" in (j := response.json)
        assert len(j["items"]) == 6


@pytest.mark.usefixtures("admin_logged_in")
class TestSwitch:
    def test_list_switches(self, client: TestClient):
        with client.renders_template("infrastructure/switches_list.html"):
            client.assert_url_ok(url_for("infrastructure.switches"))

    def test_switches_json(self, client: TestClient, switch):
        response = client.assert_url_ok(url_for("infrastructure.switches_json"))
        assert "items" in (j := response.json)
        assert len(j["items"]) == 1
        [it] = j["items"]
        assert it["id"] == switch.host_id
        assert "edit_link" in it
        assert "delete_link" in it

    def test_show_nonexistent_switch(self, client: TestClient):
        with client.flashes_message("nicht gefunden", "error"):
            client.assert_url_redirects(
                url_for("infrastructure.switch_show", switch_id=999),
                expected_location=url_for("infrastructure.switches"),
            )

    def test_show_switch(self, client: TestClient, switch: Switch):
        with client.renders_template("infrastructure/switch_show.html"):
            client.assert_url_ok(
                url_for("infrastructure.switch_show", switch_id=switch.host_id)
            )

    def test_show_nonexistent_switch_table(self, client: TestClient):
        client.assert_url_response_code(
            url_for("infrastructure.switch_show_json", switch_id=999),
            code=404,
        )

    def test_show_switch_table(self, client: TestClient, switch: Switch):
        response = client.assert_url_ok(
            url_for("infrastructure.switch_show_json", switch_id=switch.host_id)
        )
        assert "items" in (j := response.json)
        assert len(j["items"]) == 1


@pytest.mark.usefixtures("admin_logged_in", "session")
class TestCreateSwitch:
    @pytest.fixture(scope="class")
    def url(self) -> str:
        return url_for("infrastructure.switch_create")

    @pytest.fixture(scope="class")
    def room(self, class_session: Session) -> Room:
        return f.RoomFactory()

    def test_create_switch_get(self, client):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url_for("infrastructure.switch_create"))

    def test_create_switch_post_no_data(self, client, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url,
                data={},
                method="POST",
            )

    def test_create_switch_post_invalid_data(self, client, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url,
                # data according to `class SwitchForm`
                data={
                    "name": "Test Switch",
                    "management_ip": "10.10.10.2",
                    # room number missing
                },
                method="POST",
            )

    def test_create_switch_post_valid_data(self, client, room, url):
        with client.flashes_message("erfolgreich erstellt", "success"):
            client.assert_url_redirects(
                url,
                # data according to `class SwitchForm`
                data={
                    "name": "Test Switch",
                    "management_ip": "10.10.10.2",
                    "room_number": room.number,
                    "level": room.level,
                    "building": room.building_id,
                },
                method="POST",
            )


@pytest.mark.usefixtures("admin_logged_in", "session")
class TestSwitchEdit:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int], str]:
        def _url(switch_id):
            return url_for("infrastructure.switch_edit", switch_id=switch_id)

        return _url

    def test_edit_nonexistent_switch(self, client, url):
        with client.flashes_message("nicht gefunden", category="error"):
            client.assert_url_redirects(url(999), url_for("infrastructure.switches"))

    def test_edit_switch_get(self, client, switch, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(switch.host_id))

    def test_edit_switch_post_no_data(self, client, switch, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(switch.host_id), data={}, method="POST")

    def test_edit_switch_post_invalid_data(self, client, switch, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url(switch.host_id),
                # data according to `class SwitchForm`
                data={
                    "name": "Test Switch",
                    "management_ip": "This is not an IP",
                    # room number missing
                },
                method="POST",
            )

    def test_edit_switch_post_valid_data(self, client, switch, url):
        with client.flashes_message("erfolgreich bearbeitet", "success"):
            client.assert_url_redirects(
                url(switch.host_id),
                # data according to `class SwitchForm`
                data={
                    "name": "Test Switch (now with new name)",
                    "management_ip": "10.10.10.3",
                    "room_number": switch.host.room.number,
                    "level": switch.host.room.level,
                    "building": switch.host.room.building_id,
                },
                method="POST",
            )


@pytest.mark.usefixtures("admin_logged_in", "session")
class TestSwitchDelete:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int], str]:
        def _url(switch_id):
            return url_for("infrastructure.switch_delete", switch_id=switch_id)

        return _url

    def test_delete_nonexistent_switch(self, client, url):
        with client.flashes_message("nicht gefunden", category="error"):
            client.assert_url_redirects(url(999), url_for("infrastructure.switches"))

    def test_delete_switch_get(self, client, switch, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(switch.host_id))

    def test_delete_switch_post(self, client, switch, url):
        with client.flashes_message("erfolgreich gelöscht", "success"):
            client.assert_url_redirects(url(switch.host_id), method="POST")


@pytest.mark.usefixtures("admin_logged_in", "session")
class TestSwitchPortCreate:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int], str]:
        def _url(switch_id):
            return url_for("infrastructure.switch_port_create", switch_id=switch_id)

        return _url

    @pytest.fixture(scope="class")
    def patch_port(self, class_session, switch) -> PatchPort:
        return f.PatchPortFactory(switch_room=switch.host.room)

    @pytest.fixture(scope="class")
    def connected_patch_port(self, class_session) -> PatchPort:
        # patch_port = f.PatchPortFactory(switch_room=switch.host.room, switch_port=sp)
        return f.PatchPortFactory(patched=True)

    def test_create_port_at_nonexistent_switch(self, client, url):
        with client.flashes_message("nicht gefunden", category="error"):
            client.assert_url_redirects(url(999), url_for("infrastructure.switches"))

    def test_create_port_get(self, client, switch, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(switch.host_id))

    def test_create_port_no_data(self, client, switch, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(switch.host_id), data={}, method="POST")

    def test_create_port_invalid_data(self, client, switch, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url(switch.host_id),
                data={
                    "name": "Test Port",
                    "patch_port": "-1",  # bad id
                },
                method="POST",
            )

    def test_create_port_valid_data(self, client, switch, patch_port, url):
        with client.flashes_message("erfolgreich erstellt", "success"):
            client.assert_url_redirects(
                url(switch.host_id),
                data={
                    "name": "Test Port",
                    "patch_port": str(patch_port.id),
                    "vlan": None,
                },
                method="POST",
            )

    def test_create_port_already_patched(
        self, client, switch, connected_patch_port, url
    ):
        resp = client.assert_url_ok(
            url(connected_patch_port.switch_port.switch.host_id),
            data={
                "name": "Test Port",
                "patch_port": str(connected_patch_port.id),
                "vlan": None,
            },
            method="POST",
        )
        assert re.search("bereits.*verbunden", string=(resp.data.decode()))


@pytest.mark.usefixtures("admin_logged_in", "session")
class TestSwitchPortEdit:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int, int], str]:
        def _url(switch_id: int, switch_port_id: int) -> str:
            return url_for(
                "infrastructure.switch_port_edit",
                switch_id=switch_id,
                switch_port_id=switch_port_id,
            )

        return _url

    @pytest.fixture(scope="class")
    def connected_patch_port(self, class_session, switch) -> PatchPort:
        return f.PatchPortFactory(patched=True, switch_port__switch=switch)

    @pytest.fixture(scope="class")
    def switch_port(self, class_session, connected_patch_port) -> SwitchPort:
        return connected_patch_port.switch_port

    @pytest.fixture(scope="class")
    def switch_port_2(self, class_session, switch) -> SwitchPort:
        return f.SwitchPortFactory(switch__host__room=switch.host.room)

    def test_get_nonexistent_switch(self, client, url):
        with client.flashes_message("nicht gefunden", category="error"):
            client.assert_url_redirects(url(999, 999))

    def test_get_nonexistent_switch_port(self, client, switch, url):
        with client.flashes_message("nicht gefunden", category="error"):
            client.assert_url_redirects(url(switch.host_id, 999))

    def test_get_switch_port_wrong_switch(self, client, switch, switch_port_2, url):
        with client.flashes_message("SwitchPort.*gehört nicht zu", category="error"):
            client.assert_url_redirects(url(switch.host_id, switch_port_2.id))

    def test_get_switch_port(self, client, switch, switch_port, url):
        client.assert_url_ok(url(switch.host_id, switch_port.id))

    def test_post_switch_port_no_data(self, client, switch, switch_port, url):
        URL = url(switch.host_id, switch_port.id)
        with client.flashes_message("erfolgreich", category="success"):
            client.assert_url_redirects(URL, data={}, method="POST")

    def test_post_switch_port_invalid_data(self, client, switch, switch_port, url):
        URL = url(switch.host_id, switch_port.id)
        bad_data = {
            "name": "Test Port",
            "patch_port": "-1",  # bad id
        }
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(URL, data=bad_data, method="POST")

    def test_edit_switch_port_new_port(self, client, session, switch, switch_port, url):
        URL = url(switch.host_id, switch_port.id)
        new_port = f.PatchPortFactory(switch_room=switch.host.room)
        session.flush()
        good_data = {
            "name": "Test Port",
            "patch_port": str(new_port.id),
            "vlan": None,
        }
        with client.flashes_message("erfolgreich", "success"):
            client.assert_url_redirects(URL, data=good_data, method="POST")

    def test_edit_switch_port_patched_port(
        self, client, switch, switch_port_2, url, connected_patch_port
    ):
        # need `switch_port_2`, so patching actually does something
        URL = url(switch_port_2.switch.host_id, switch_port_2.id)
        data = {
            "name": "Test Port",
            "patch_port": str(connected_patch_port.id),
            "vlan": None,
        }
        with client.renders_template("generic_form.html"):
            resp = client.assert_url_ok(URL, data=data, method="POST")
        assert re.search("bereits.*verbunden", string=(resp.data.decode()))


@pytest.mark.usefixtures("admin_logged_in", "session")
class TestSwitchPortDelete:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int, int], str]:
        def _url(switch_id: int, switch_port_id: int) -> str:
            return url_for(
                "infrastructure.switch_port_delete",
                switch_id=switch_id,
                switch_port_id=switch_port_id,
            )

        return _url

    @pytest.fixture(scope="class")
    def switch_port(self, class_session, switch):
        return f.SwitchPortFactory(switch=switch)

    @pytest.fixture(scope="class")
    def switch_port_2(self, class_session, switch) -> SwitchPort:
        return f.SwitchPortFactory(switch__host__room=switch.host.room)

    def test_delete_nonexistent_switch(self, client, url):
        with client.flashes_message("nicht gefunden", category="error"):
            client.assert_url_redirects(url(999, 999))

    def test_delete_nonexistent_switch_port(self, client, switch, url):
        with client.flashes_message("nicht gefunden", category="error"):
            client.assert_url_redirects(url(switch.host_id, 999))

    def test_delete_switch_port_other_switch(self, client, switch_port_2, switch, url):
        with client.flashes_message("SwitchPort.*gehört nicht zu", category="error"):
            client.assert_url_redirects(url(switch.host_id, switch_port_2.id))

    def test_delete_switch_port_get(self, client, switch, switch_port, url):
        client.assert_url_ok(url(switch.host_id, switch_port.id))

    def test_delete_switch_port_post(self, client, switch, switch_port, url):
        URL = url(switch.host_id, switch_port.id)
        with client.flashes_message("erfolgreich", category="success"):
            client.assert_url_redirects(URL, method="POST")
