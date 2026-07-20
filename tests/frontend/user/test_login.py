#  Copyright (c) 2026. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import pytest
import requests
from bs4 import BeautifulSoup
from flask import url_for
from sqlalchemy.orm import Session

from tests.factories import UserFactory
from tests.frontend.assertions import TestClient
from web import PycroftFlask


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.mark.usefixtures("session")
class TestUserOidcLogin:
    @pytest.fixture(scope="class")
    def user(self, class_session: Session):
        user = UserFactory(
            login="agdsn",
        )
        class_session.flush()
        return user

    def test_disabled_login(self, client: TestClient, app: PycroftFlask, user: UserFactory):
        app.config["OIDC_ENABLED"] = False
        app.config["OIDC_TESTING_PROFILE"] = {
            "email": "email",
            "preferred_username": "agdsn",
            "groups": ["mitgliederverwalter"],
        }
        with client.flashes_message("Erfolgreich angemeldet.", category="success"):
            response = client.get(url_for("login.login"))
            assert response.status_code == 302
            assert response.location == url_for("user.overview")

        client.get("/logout")

    def test_callback_flow(self, client: TestClient, app: PycroftFlask):
        app.config["OIDC_ENABLED"] = True
        response_redirect_to_oidc = client.get(url_for("login.openid_connect"))
        assert response_redirect_to_oidc.status_code == 302
        location = response_redirect_to_oidc.location

        session = requests.Session()
        oidc_open_response = session.get(location, allow_redirects=False)
        assert oidc_open_response.status_code == 200, "Keycloak Auth-Endpoint nicht erreichbar"

        soup = BeautifulSoup(oidc_open_response.text, "html.parser")
        action_url = soup.find("form")["action"]
        oidc_login_response = session.post(
            action_url,
            data={"username": "agdsn", "password": "password"},
            allow_redirects=False,
        )
        assert oidc_login_response.status_code == 302
        response_url = oidc_login_response.headers["Location"]

        with client.flashes_message("Erfolgreich angemeldet.", category="success"):
            response_redirect_to_oidc = client.get(
                response_url.removeprefix("http://localhost:5000")
            )
            assert response_redirect_to_oidc.status_code == 302
            assert response_redirect_to_oidc.location == url_for("user.overview")
