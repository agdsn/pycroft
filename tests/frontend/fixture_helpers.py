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
        raise AssertionError(f"Cannot create mock argument for {e.args[0]}") from e
    return url_adapter.build(rule.endpoint, values)


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


def _serialize_key_val_pair(key: str, val: t.Any) -> t.Iterable[t.Any]:
    match val:
        case str():
            yield key, val
            return
        case list() as xs:
            for i, x in enumerate(xs, start=1):
                # assertion: term depth of x < term depth of val
                yield from _serialize_key_val_pair(f"{key}-{i}", x)
            return
        case dict() as d:
            for k, v in d.items():
                yield from _serialize_key_val_pair(f"{key}-{k}", v)
        case _:
            yield key, val


def serialize_formdata(d: dict[str, t.Any]) -> dict[str, t.Any]:
    """Serialize a nested python object into flat formdata.

    Useful to produce formdata form POST requests in testing.

    Spec:

    - The operation happens element-wise (with respect to key-value pairs)
    - The operation descends recursively into nested lists and dicts
    - ``{key: x}`` will be mapped to ``{key: x}`` for non-iterable ``x``
    - ``{key: [a, b]}`` will be flattened to ``{f"{key}-1": a, f"{key}-2": b}``
    - ``{key: {"foo": "bar"}}`` will be flattened to ``{f"{key}-foo": "bar"}``
    """
    return {
        new_key: new_val
        for key, val in d.items()
        for new_key, new_val in _serialize_key_val_pair(key, val)
    }
