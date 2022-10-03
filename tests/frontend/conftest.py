import typing as t

import pytest
from flask import _request_ctx_stack
from sqlalchemy.orm import Session

from pycroft import Config
from pycroft.model.user import User
from tests.factories import UserFactory, AdminPropertyGroupFactory, ConfigFactory
from web import make_app, PycroftFlask
from .assertions import TestClient
from .fixture_helpers import login_context, BlueprintUrls, _build_rule, prepare_app_for_testing


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


@pytest.fixture(scope="module")
def processor(module_session, test_client) -> t.Iterator[User]:
    """A user (member of the admin group) who has been logged in.

    Module-scoped, i.e. every module with a test using this fixture will have this user logged in!
    """
    login = "shoot-the-root"
    password = "password"
    user = UserFactory(
        login=login,
        # password=password,  # hash already defaults to `password`
        with_membership=True,
        membership__group=AdminPropertyGroupFactory.create(),
    )
    with login_context(test_client=test_client, login=login, password=password):
        yield user


@pytest.fixture(scope="session")
def blueprint_urls(flask_app: PycroftFlask) -> BlueprintUrls:
    def _blueprint_urls(blueprint_name: str) -> list[str]:
        return [
            _build_rule(_request_ctx_stack.top.url_adapter, rule)
            for rule in flask_app.url_map.iter_rules()
            if rule.endpoint.startswith(f"{blueprint_name}.")
        ]
    return _blueprint_urls
