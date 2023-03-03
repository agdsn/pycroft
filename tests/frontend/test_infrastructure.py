# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import pytest
from sqlalchemy.orm import Session
from flask import url_for

from pycroft.model.host import Switch
from tests.factories import SwitchFactory
from .assertions import TestClient


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


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

    def test_show_switch(self, client: TestClient, switch: Switch):
        with client.renders_template("infrastructure/switch_show.html"):
            client.assert_url_ok(
                url_for("infrastructure.switch_show", switch_id=switch.host_id)
            )

    def test_show_switch_table(self, client: TestClient, switch: Switch):
        response = client.assert_url_ok(
            url_for("infrastructure.switch_show_json", switch_id=switch.host_id)
        )
        assert "items" in (j := response.json)
        assert len(j["items"]) == 1
