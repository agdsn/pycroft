#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import contextlib
import typing as t

import flask.testing
import jinja2 as j
import pytest
from flask import url_for, template_rendered


class TestClient(flask.testing.FlaskClient):
    __test__ = False

    if t.TYPE_CHECKING:
        def get(self, *a, **kw) -> flask.Response: ...

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.test_client = self

    def assert_url_response_code(self, url: str, status: int) -> None:
        resp = self.get(url)
        assert resp.status_code == status, \
            f"Expected url {url} to return {status}, got {resp.status_code}"

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

    def assert_url_forbidden(self, url: str):
        resp = self.get(url)
        status = resp.status_code
        assert (
            status == 403
        ), f"Access to {url} expected to be forbidden, got status {status}"

    def assert_forbidden(self, endpoint: str):
        self.assert_url_forbidden(url_for(endpoint))

    @contextlib.contextmanager
    def renders_template(self, template: str, allow_others: bool = False):
        app = self.application
        recorded: list[tuple[j.Template, t.Any]] = []

        def record(sender, template, context, **extra):
            recorded.append((template, context))

        template_rendered.connect(record, app)
        try:
            yield
        finally:
            template_rendered.disconnect(record, app)

        if not recorded:
            pytest.fail(f"No template has been rendered (expected {template} to be used)")

        template_names = [template.name for template, ctx in recorded]
        if allow_others:
            assert template in template_names, \
                f"Expected template {template} to be rendered, got {template_names!r}"
        else:
            assert template_names == [template], \
                f"Expected template {template} to be rendered (exclusively), got {template_names!r}"


