#  Copyright (c) 2026. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import pytest
from flask import url_for
from sqlalchemy.orm import Session

from tests.factories import UserFactory
from tests.frontend.assertions import TestClient


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.mark.usefixtures("session")
class TestUserOidcLogin:
    @pytest.fixture(scope="class")
    def user(self, class_session: Session):
        user = UserFactory(
            login="oidc",
        )
        class_session.flush()
        return user

    def test_oidc_login(self, client: TestClient, app, user):
        with client.flashes_message("Erfolgreich angemeldet.", category="success"):
            response = client.get(url_for("login.login"))
            assert response.status_code == 302
            assert response.location == url_for("user.overview")
