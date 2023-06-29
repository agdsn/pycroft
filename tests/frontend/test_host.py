# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import pytest
from flask import url_for

from pycroft.model.host import Host
from pycroft.model.user import User
from tests import factories as f

from .assertions import TestClient


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.fixture(scope="module")
def owner(module_session) -> User:
    return f.UserFactory()


@pytest.fixture(scope="module")
def host(module_session, owner) -> Host:
    return f.HostFactory(owner=owner)


@pytest.mark.usefixtures("admin_logged_in")
class TestHostDelete:
    def test_delete_nonexistent_host(self, client):
        client.assert_url_response_code(
            url_for("host.host_delete", host_id=999), code=404
        )

    def test_host_delete_successful(self, session, client, host, owner):
        with client.flashes_message("Host.*gelöscht", category="success"):
            client.assert_url_redirects(
                url_for("host.host_delete", host_id=host.id),
                method="POST",
            )
        session.refresh(owner)
        assert owner.hosts == []

    def test_host_get_returns_form(self, client, host):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url_for("host.host_delete", host_id=host.id))
