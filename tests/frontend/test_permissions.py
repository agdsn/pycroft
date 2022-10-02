# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing as t

import pytest
from flask import url_for, current_app
from flask.testing import FlaskClient
from jinja2.runtime import Context

from tests.factories.property import FinancePropertyGroupFactory, \
    AdminPropertyGroupFactory, MembershipFactory
from tests.factories.user import UserFactory
from tests.frontend.legacy_base import FrontendDataTestBase
from tests.legacy_base import FactoryDataTestBase, FactoryWithConfigDataTestBase
from web import PycroftFlask
from web.template_filters import require


class PermissionsTestBase(FrontendDataTestBase, FactoryWithConfigDataTestBase):
    password = 'password'
    admin_login = 'testadmin2'
    finance_login = 'finanzer'
    member_login = 'regular'

    def create_factories(self):
        super().create_factories()
        self.admin_group = AdminPropertyGroupFactory.create()
        self.admin = UserFactory.create(
            login=self.admin_login,
            password=self.password,
            with_membership=True,
            membership__group=self.admin_group,
            membership__includes_today=True,
        )
        self.finance_group = FinancePropertyGroupFactory.create()
        self.head_of_finance = UserFactory.create(
            login=self.finance_login,
            password=self.password,
            with_membership=True,
            membership__group=self.finance_group,
            membership__includes_today=True,
        )
        # finanzer is also an admin
        MembershipFactory.create(group=self.admin_group, user=self.head_of_finance,
                                 includes_today=True)
        self.member = UserFactory.create(
            login=self.member_login,
            password=self.password,
            with_membership=True,
            membership__group=self.config.member_group,
            membership__includes_today=True,
        )


class TestAnonymous:
    """First test as anonymous user.
    Anonymous users should be able to access the login page and the /static/
    content, nothing else.
    """
    @pytest.fixture(scope="class")
    def assert_response_code(self, test_client: FlaskClient) -> t.Callable[[str, int], None]:
        def _assert(url: str, status: int) -> None:
            resp = test_client.get(url)
            assert resp.status_code == status
        return _assert

    @pytest.fixture(scope='class')
    def jinja_context(self, flask_app: PycroftFlask) -> Context:
        return Context(flask_app.jinja_env, parent=None, name="pseudo", blocks={})

    def test_access_anonymous(self, assert_response_code, jinja_context):
        # Login is OK
        assert_response_code(url_for('login.login'), 200)

        # Fetching static content is OK
        assert_response_code(require(jinja_context, 'main.css'), 200)

        # Access to other pages/blueprints is NOT OK
        assert_response_code(url_for('finance.bank_accounts_list'), 302)
        assert_response_code(url_for('infrastructure.switches'), 302)


class Test_020_Permissions_Admin(PermissionsTestBase):
    """Test permissions for admin usergroup.
    """

    def setUp(self):
        self.login = self.admin_login
        super().setUp()

    def test_0010_access_buildings(self):
        # Admin has access to view the facilities overview
        self.assert_response_code(url_for('facilities.overview'), 200)

    def test_0020_access_finance(self):
        # Admin has no access to finance
        self.assert_access_forbidden(url_for('finance.bank_accounts_list'))


class Test_030_Permissions_Finance(PermissionsTestBase):
    """Test permissions for finance usergroup (advanced).
    """
    def setUp(self):
        self.login = self.finance_login
        super().setUp()

    def test_0010_access_buildings(self):
        self.assert_response_code(url_for('facilities.overview'), 200)

    def test_0020_access_finance(self):
        self.assert_response_code(url_for('finance.bank_accounts_list'), 200)


class Test_040_Permissions_User(PermissionsTestBase):
    """Test permissions as a user without any membership
    """

    def setUp(self):
        self.login = self.member_login
        super().setUp()

    def test_0010_access_user(self):
        for url in self.blueprint_urls(current_app, 'user'):
            self.assert_access_forbidden(url)

    def test_0020_access_finance(self):
        for url in self.blueprint_urls(current_app, 'finance'):
            self.assert_access_forbidden(url)

    def test_0030_access_buildings(self):
        for url in self.blueprint_urls(current_app, 'facilities'):
            self.assert_access_forbidden(url)

    def test_0040_access_infrastructure(self):
        for url in self.blueprint_urls(current_app, 'infrastructure'):
            self.assert_access_forbidden(url)

    def test_0050_access_properties(self):
        for url in self.blueprint_urls(current_app, 'properties'):
            self.assert_access_forbidden(url)

    def test_0060_access_login(self):
        # Login see Test_010_Anonymous
        #TODO assert client response by text or better, not code
        self.assert_response_code(url_for('login.logout'), 302)
