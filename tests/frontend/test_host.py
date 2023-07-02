# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing as t

import pytest
from flask import url_for

import web.blueprints.host
from pycroft.exc import PycroftException
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
    return f.HostFactory(owner=owner, room__patched_with_subnet=True)


@pytest.mark.usefixtures("admin_logged_in")
class TestHostDelete:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int], str]:
        def _url(host_id: int) -> str:
            return url_for("host.host_delete", host_id=host_id)

        return _url

    def test_delete_nonexistent_host(self, client, url):
        client.assert_url_response_code(url(999), code=404)

    def test_host_delete_successful(self, session, client, host, owner, url):
        with client.flashes_message("Host.*gelöscht", category="success"):
            client.assert_url_redirects(url(host.id), method="POST")
        session.refresh(owner)
        assert owner.hosts == []

    def test_host_get_returns_form(self, client, host, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(host.id))

    def test_host_delete_exception(self, client, host, url, monkeypatch):
        def _r(*a, **kw):
            raise PycroftException

        monkeypatch.setattr(web.blueprints.host.lib_host, "host_delete", _r)

        with client.flashes_message("Fehler aufgetreten", category="error"):
            client.assert_url_ok(url(host.id), method="POST")


@pytest.mark.usefixtures("admin_logged_in")
class TestHostEdit:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int], str]:
        def _url(host_id: int) -> str:
            return url_for("host.host_edit", host_id=host_id)

        return _url

    def test_edit_nonexistent_host(self, client, url):
        client.assert_url_response_code(url(999), code=404)

    def test_edit_host_get(self, client, host, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(host.id))

    def test_post_without_data(self, client, host, url):
        """works because the room data is automatically derived from the host"""
        # HTTP 200 OK although form invalid
        client.assert_url_ok(url(host.id), method="POST")

    def test_post_with_data(self, client, host, url):
        with client.flashes_message("Host.*bearbeitet", category="success"):
            client.assert_url_redirects(
                url(host.id),
                method="POST",
                data={
                    "owner": host.owner.id,
                    "name": f"new-{host.name}",
                    "building": host.room.building.id,
                    "level": host.room.level,
                    "room_number": host.room.number,
                },
            )

    def test_post_with_invalid_data(self, client, host, url):
        client.assert_url_ok(
            url(host.id),
            method="POST",
            data={
                "owner": host.owner.id,
                "name": f"new-{host.name}",
                "building": host.room.building.id,
                "level": host.room.level,
                "room_number": 999,
            },
        )


@pytest.mark.usefixtures("admin_logged_in")
class TestHostCreate:
    @pytest.fixture(scope="class")
    def url(self) -> t.Callable[[int], str]:
        def _url(user_id: int) -> str:
            return url_for("host.host_create", user_id=user_id)

        return _url

    def test_create_host_nonexistent_owner(self, client, url):
        client.assert_url_response_code(url(999), code=404)

    def test_create_host_get(self, client, owner, url):
        with client.renders_template("generic_form.html"):
            client.assert_url_ok(url(owner.id))

    def test_create_host_post(self, session, client, owner, host, url):
        with client.flashes_message("Host.*erstellt", category="success"):
            client.assert_url_redirects(
                url(owner.id),
                method="POST",
                data={
                    "name": "test-host",
                    "building": owner.room.building.id,
                    "level": owner.room.level,
                    "room_number": owner.room.number,
                },
            )
            session.refresh(owner)
            # assert len(owner.hosts) == 1
            # assert owner.hosts[0].name == "test-host"
            new_hosts = set(owner.hosts) - {host}
            assert len(new_hosts) == 1
            assert list(new_hosts)[0].name == "test-host"

    def test_create_host_post_invalid_data(self, session, client, owner, url):
        client.assert_url_ok(
            url(owner.id),
            method="POST",
            data={
                "name": "test-host",
                "building": owner.room.building.id,
                "level": owner.room.level,
                "room_number": 999,
            },
        )
        session.refresh(owner)
        assert len(owner.hosts) == 1


def test_user_hosts(client, host):
    resp = client.assert_url_ok(url_for("host.user_hosts_json", user_id=host.owner.id))

    assert "items" in resp.json
    items = resp.json["items"]
    assert len(items) == 1
    [item] = items
    assert item["switch"]
    assert item["port"]
    assert item["id"] == host.id
    assert len(item["actions"]) == 2


@pytest.fixture()
def host_without_room(session):
    return f.HostFactory(room=None)


def test_user_host_without_room(client, host_without_room):
    resp = client.assert_url_ok(
        url_for("host.user_hosts_json", user_id=host_without_room.owner.id)
    )
    assert len(resp.json["items"]) == 1
    [it] = resp.json["items"]
    assert it["switch"] is None
    assert it["port"] is None
