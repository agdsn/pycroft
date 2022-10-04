# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import pytest
from jinja2.runtime import Context
from sqlalchemy.orm import Session

from pycroft.model.config import Config
from pycroft.model.user import PropertyGroup, User
from tests.factories.property import FinancePropertyGroupFactory, \
    AdminPropertyGroupFactory, MembershipFactory
from tests.factories.user import UserFactory
from web import PycroftFlask
from web.template_filters import require
from .assertions import TestClient
from .fixture_helpers import login_context, BlueprintUrls


@pytest.fixture(scope="module")
def admin_group(module_session: Session):
    return AdminPropertyGroupFactory.create()


@pytest.fixture(scope="module")
def test_client(module_test_client: TestClient) -> TestClient:
    return module_test_client


class TestAnonymous:
    """First test as anonymous user.
    Anonymous users should be able to access the login page and the /static/
    content, nothing else.
    """
    @pytest.fixture(scope='class')
    def jinja_context(self, flask_app: PycroftFlask) -> Context:
        return Context(flask_app.jinja_env, parent=None, name="pseudo", blocks={})

    def test_login_page_visible(self, test_client: TestClient):
        test_client.assert_ok('login.login')

    def test_static_content_can_be_fetched(self, test_client: TestClient, jinja_context: Context):
        test_client.assert_url_ok(require(jinja_context, 'main.css'))

    def test_finance_denied(self, test_client: TestClient):
        test_client.assert_response_code('finance.bank_accounts_list', 302)

    def test_infrastructure_denied(self, test_client: TestClient):
        test_client.assert_response_code('infrastructure.switches', 302)

    def test_user_denied(self, test_client: TestClient):
        test_client.assert_response_code('user.overview', 302)


class TestPermissionsAdmin:
    """Test permissions for admin usergroup.
    """
    @pytest.fixture(scope="class", autouse=True)
    def admin_logged_in(self, admin: User, test_client: TestClient):
        with login_context(test_client, admin.login, "password"):
            yield

    def test_access_buildings(self, test_client: TestClient):
        test_client.assert_ok("facilities.overview")

    def test_access_finance(self, test_client: TestClient):
        test_client.assert_forbidden("finance.bank_accounts_list")


class TestPermissionsFinance:
    """Test permissions for finance usergroup (advanced).
    """
    @pytest.fixture(scope="class", autouse=True)
    def treasurer_logged_in(
        self,
        treasurer: User,
        test_client: TestClient,
    ) -> None:
        with login_context(test_client, treasurer.login, "password"):
            yield

    def test_access_buildings(self, test_client: TestClient):
        test_client.assert_ok("facilities.overview")

    def test_access_finance(self, test_client: TestClient):
        test_client.assert_ok("finance.bank_accounts_list")


class TestPermissionsUser:
    """Test permissions as a user without any membership
    """
    @pytest.fixture(scope="class", autouse=True)
    def member_logged_in(
        self, class_session: Session, config: Config, test_client: TestClient
    ):
        UserFactory.create(
            login="member",
            with_membership=True,
            membership__group=config.member_group,
            membership__includes_today=True,
        )
        class_session.flush()
        with login_context(test_client, "member", "password"):
            yield

    def test_access_user(
        self, test_client: TestClient, blueprint_urls: BlueprintUrls
    ):
        for url in blueprint_urls("user"):
            test_client.assert_url_forbidden(url)

    def test_access_finance(
        self, test_client: TestClient, blueprint_urls: BlueprintUrls
    ):
        for url in blueprint_urls("finance"):
            test_client.assert_url_forbidden(url)

    def test_access_buildings(
        self, test_client: TestClient, blueprint_urls: BlueprintUrls
    ):
        for url in blueprint_urls("facilities"):
            test_client.assert_url_forbidden(url)

    def test_access_infrastructure(
        self, test_client: TestClient, blueprint_urls: BlueprintUrls
    ):
        for url in blueprint_urls("infrastructure"):
            test_client.assert_url_forbidden(url)

    def test_access_properties(
        self, test_client: TestClient, blueprint_urls: BlueprintUrls
    ):
        for url in blueprint_urls("properties"):
            test_client.assert_url_forbidden(url)

    def test_access_login(
        self, test_client: TestClient, blueprint_urls: BlueprintUrls
    ):
        # Login see Test_010_Anonymous
        #TODO assert client response by text or better, not code
        test_client.assert_response_code("login.logout", 302)
