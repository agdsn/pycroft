# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import pytest
from flask import url_for

from pycroft.model.host import Host, Interface
from tests import factories as f

from .assertions import TestClient


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.fixture(scope="module", autouse=True)
def host(module_session) -> Host:
    return f.HostFactory(interface=None)


@pytest.fixture(scope="module", autouse=True)
def interface(module_session, host) -> Interface:
    return f.InterfaceFactory(host=host)


pytestmark = pytest.mark.usefixtures("admin_logged_in")


@pytest.mark.usefixtures("session")
class TestInterfaceDelete:
    def test_delete_nonexistent_interface(self, client):
        client.assert_url_response_code(
            url_for("host.interface_delete", interface_id=999), code=404
        )

    def test_delete_interface_get(self, client, interface):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url_for("host.interface_delete", interface_id=interface.id)
            )

    def test_delete_interface_post(self, session, client, interface, host):
        with client.flashes_message("Interface.*gelöscht", category="success"):
            client.assert_url_redirects(
                url_for("host.interface_delete", interface_id=interface.id),
                method="POST",
            )
        session.refresh(host)
        assert interface not in host.interfaces


@pytest.mark.usefixtures("session")
class TestInterfaceEdit:
    def test_edit_nonexistent_interface(self, client):
        client.assert_url_response_code(
            url_for("host.interface_edit", interface_id=999), code=404
        )

    def test_edit_interface_get(self, client, interface):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url_for("host.interface_edit", interface_id=interface.id)
            )

    def test_edit_interface_post_invalid_data(self, client, interface):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(
                url_for("host.interface_edit", interface_id=interface.id),
                data={"mac": "invalid"},
                method="POST",
            )

    def test_edit_interface_success(self, session, client, interface):
        with client.flashes_message("Interface.*bearbeitet", category="success"):
            client.assert_url_redirects(
                url_for("host.interface_edit", interface_id=interface.id),
                method="POST",
                data={"mac": "00:11:22:33:44:55", "name": "new name"},
            )
        session.refresh(interface)
        assert interface.mac == "00:11:22:33:44:55"
        assert interface.name == "new name"