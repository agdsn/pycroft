#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing as t

import flask.testing
from flask import url_for


class TestClient(flask.testing.FlaskClient):
    if t.TYPE_CHECKING:
        def get(self, *a, **kw) -> flask.Response: ...

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.test_client = self

    def assert_url_response_code(self, url: str, status: int) -> None:
        resp = self.get(url)
        assert resp.status_code == status

    def assert_response_code(self, endpoint: str, status: int) -> None:
        self.assert_url_response_code(url_for(endpoint), status)

    def assert_url_ok(self, url: str):
        self.assert_url_response_code(url, status=200)

    def assert_ok(self, endpoint: str):
        self.assert_response_code(endpoint, status=200)


    def assert_url_redirects(self, url: str, expected_location: str | None = None):
        resp = self.get(url)
        assert 300 <= resp.status_code < 400, \
            f"Expected {url!r} to redirect, got status {resp.status}"
        if expected_location is None:
            return
        assert resp.location == expected_location

    def assert_redirects(self, endpoint: str, expected_location: str | None = None):
        resp = self.get(url_for(endpoint))
        assert 300 <= resp.status_code < 400, \
            f"Expected endpoint {endpoint} to redirect, got status {resp.status}"
        if expected_location is None:
            return
        assert resp.location == expected_location
