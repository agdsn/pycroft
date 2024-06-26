import contextlib
import typing as t

import pytest
from flask.globals import request_ctx
from sqlalchemy.orm import Session

from pycroft import Config
from pycroft.model.user import User, PropertyGroup
from tests.factories import UserFactory, AdminPropertyGroupFactory, ConfigFactory
from web import PycroftFlask
from .assertions import TestClient
from .fixture_helpers import login_context, BlueprintUrls, _build_rule, prepare_app_for_testing
from ..factories.property import FinancePropertyGroupFactory, MembershipFactory


@pytest.fixture(scope="session")
def app() -> PycroftFlask:
    """A fully configured flask app for frontend tests"""
    from web import make_app
    return prepare_app_for_testing(make_app())


@contextlib.contextmanager
def _test_client(app: PycroftFlask) -> t.Iterator[TestClient]:
    app.test_client_class = TestClient
    with app.app_context(), app.test_client() as c:
        yield c


@pytest.fixture(scope="module")
def module_test_client(app: PycroftFlask) -> t.Iterator[TestClient]:
    """An activated test client with app context.

    depends on `app`, which can be overridden.

    .. tip:: it might be helpful to “rename” this fixture like this:
        >>> @pytest.fixture
        >>> def client(module_test_client: TestClient) -> TestClient:
        ...     return module_test_client
    """
    with _test_client(app) as c:
        yield c


@pytest.fixture(scope="class")
def class_test_client(app: PycroftFlask) -> t.Iterator[TestClient]:
    """Like :func:`module_test_client`.

    This fixture exists, so you can override `app` with something `class`-scoped:

    >>> from flask import Flask
    >>> class TestWithCustomApp:
    ...     @pytest.fixture(scope="class")
    ...     def app(self) -> Flask:
    ...        return Flask("naked_test_app")
    ...
    >>>     @pytest.fixture(scope="class")
    >>>     def client(self, class_test_client: TestClient) -> TestClient:
    ...         return class_test_client
    """
    with _test_client(app) as c:
        yield c


@pytest.fixture(scope="module")
def config(module_session: Session) -> Config:
    config = ConfigFactory.create()
    module_session.flush()
    return config


@pytest.fixture(scope="session")
def blueprint_urls(app: PycroftFlask) -> BlueprintUrls:
    def _blueprint_urls(
        blueprint_name: str, methods: set[str] = {"GET", "POST"}  # noqa: B006
    ) -> list[str]:
        return [
            (_build_rule(request_ctx.url_adapter, rule), method)
            for rule in app.url_map.iter_rules()
            for method in rule.methods & methods
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
def admin_logged_in(admin: User, module_test_client: TestClient) -> None:
    """A module-scoped convenience fixture to log in an admin"""
    with login_context(module_test_client, admin.login, "password"):
        yield


@pytest.fixture(scope="module")
def treasurer_logged_in(treasurer: User, module_test_client: TestClient) -> None:
    """A module-scoped convenience fixture to log in an admin"""
    with login_context(module_test_client, treasurer.login, "password"):
        yield
