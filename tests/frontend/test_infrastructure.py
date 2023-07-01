# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import pytest
from ipaddr import IPv4Network, IPv4Address
from sqlalchemy.orm import Session
from flask import url_for

from pycroft.model.host import Switch
from pycroft.model.net import Subnet
from tests import factories as f
from tests.factories import SwitchFactory
from web.blueprints.infrastructure import format_address_range
from .assertions import TestClient


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
    @pytest.fixture(scope="class")
    def switch(self, class_session: Session) -> Switch:
        switch = SwitchFactory()
        class_session.flush()
        return switch

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
