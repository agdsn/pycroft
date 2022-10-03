import typing as t

import pytest
from flask import _request_ctx_stack
from sqlalchemy.orm import Session

from pycroft import Config
from pycroft.model.user import User, PropertyGroup
from tests.factories import UserFactory, AdminPropertyGroupFactory, ConfigFactory
from web import make_app, PycroftFlask
from .assertions import TestClient
from .fixture_helpers import login_context, BlueprintUrls, _build_rule, prepare_app_for_testing
from ..factories.property import FinancePropertyGroupFactory, MembershipFactory


@pytest.fixture(scope='session')
def app():
    """A minimal app for when you just need an app context"""
    return make_app()


@pytest.fixture(scope="session")
def flask_app() -> PycroftFlask:
    """A fully configured flask app for frontend tests"""
    from web import make_app
    return prepare_app_for_testing(make_app())


@pytest.fixture(scope="session")
def test_client(flask_app: PycroftFlask) -> t.Iterator[TestClient]:
    flask_app.test_client_class = TestClient
    with flask_app.app_context(), flask_app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def config(module_session: Session) -> Config:
    config = ConfigFactory.create()
    module_session.flush()
    return config


@pytest.fixture(scope="session")
def blueprint_urls(flask_app: PycroftFlask) -> BlueprintUrls:
    def _blueprint_urls(blueprint_name: str) -> list[str]:
        return [
            _build_rule(_request_ctx_stack.top.url_adapter, rule)
            for rule in flask_app.url_map.iter_rules()
            if rule.endpoint.startswith(f"{blueprint_name}.")
        ]
    return _blueprint_urls


@pytest.fixture(scope="module")
def admin_group(module_session) -> PropertyGroup:
    return AdminPropertyGroupFactory.create()


@pytest.fixture(scope="module")
def admin(module_session: Session, admin_group, config: Config) -> User:
    admin = UserFactory.create(
        login="testadmin2",
        with_membership=True,
        membership__group=AdminPropertyGroupFactory.create(),
        membership__includes_today=True,
    )
    module_session.flush()
    return admin


@pytest.fixture(scope="module")
def treasurer(module_session: Session, admin_group: PropertyGroup) -> User:
    treasurer = UserFactory.create(
        login="treasurer",
        with_membership=True,
        membership__group=FinancePropertyGroupFactory.create(),
        membership__includes_today=True,
    )
    MembershipFactory.create(user=treasurer, group=admin_group, includes_today=True)
    module_session.flush()
    return treasurer


@pytest.fixture(scope="module")
def admin_logged_in(admin: User, test_client: TestClient) -> None:
    with login_context(test_client, admin.login, "password"):
        yield
