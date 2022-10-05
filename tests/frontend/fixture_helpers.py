#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""Fixture helpers, like context managers

Exists because it is bad practice to import from `helpers`.
"""

import contextlib
import random
import string
import typing as t

from flask import url_for
from werkzeug.routing import IntegerConverter, UnicodeConverter

from .assertions import TestClient


@contextlib.contextmanager
def login_context(test_client: TestClient, login: str, password: str):
    test_client.post(
        url_for("login.login"), data={"login": login, "password": password}
    )
    yield
    test_client.get("/logout")


BlueprintUrls: t.TypeAlias = t.Callable[[str], list[str]]
_argument_creator_map = {
    IntegerConverter: lambda c: 1,
    UnicodeConverter: lambda c: "test",
}


def _default_argument_creator(_c):
    return "default"


def _build_rule(url_adapter, rule) -> str:
    try:
        values = {
            k: _argument_creator_map.get(type(v), _default_argument_creator)(v)
            for k, v in rule._converters.items()
        }
    except KeyError as e:
        raise AssertionError(f"Cannot create mock argument for {e.args[0]}")
    return url_adapter.build(rule.endpoint, values, 'GET')


def prepare_app_for_testing(app):
    """Set setting which are relevant for testing.

    * testing / debug mode
    * disable CSRF for WTForms
    * set a random secret key
    * set the server name to `localhost`
    """
    app.testing = True
    app.debug = True
    # Disable the CSRF in testing mode
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "".join(
        random.choice(string.ascii_letters) for _ in range(20)
    )
    app.config["SERVER_NAME"] = "localhost.localdomain"
    return app
