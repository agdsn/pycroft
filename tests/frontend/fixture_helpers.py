#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""Fixture helpers, like context managers

Exists because it is bad practice to import from `helpers`.
"""

import contextlib

from flask import url_for

from tests.frontend.assertions import TestClient


@contextlib.contextmanager
def login_context(test_client: TestClient, login: str, password: str):
    test_client.post(
        url_for("login.login"), data={"login": login, "password": password}
    )
    yield
    test_client.get("/logout")
