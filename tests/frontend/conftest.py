import contextlib
import random
import string
import typing as t

import pytest
from flask import url_for
from sqlalchemy.orm import close_all_sessions, scoped_session, sessionmaker, \
    Session

from pycroft.model import session as pyc_session
from pycroft.model.user import User
from tests.factories import UserFactory, AdminPropertyGroupFactory
from web import make_app, PycroftFlask
from .assertions import TestClient
from ..legacy_base import setup, get_engine_and_connection, teardown


@pytest.fixture(scope='session')
def connection(request):
    request.addfinalizer(teardown)
    setup()
    _, conn = get_engine_and_connection()
    assert conn is not None
    return conn


def rollback(transaction):
    pyc_session.session.rollback()
    pyc_session.Session.remove()
    # Rollback the outer transaction to the savepoint
    assert transaction is not None
    transaction.rollback()
    close_all_sessions()


@pytest.fixture
def session(connection, request) -> Session:
    transaction = connection.begin_nested()
    request.addfinalizer(lambda: rollback(transaction))
    s = scoped_session(sessionmaker(bind=connection))
    pyc_session.set_scoped_session(s)
    return s


@pytest.fixture(scope='session')
def app():
    return make_app()


@pytest.fixture(scope="session")
def flask_app() -> PycroftFlask:
    from web import make_app

    app = make_app()

    app.testing = True
    app.debug = True

    # Disable the CSRF in testing mode
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "".join(
        random.choice(string.ascii_letters) for _ in range(20)
    )
    app.config["SERVER_NAME"] = "localhost"

    return app


@pytest.fixture(scope="session")
def test_client(flask_app: PycroftFlask) -> t.Iterator[TestClient]:
    flask_app.test_client_class = TestClient
    with flask_app.app_context(), flask_app.test_client() as c:
        yield c


@contextlib.contextmanager
def login_context(test_client: TestClient, login: str, password: str):
    test_client.post(
        url_for("login.login"), data={"login": login, "password": password}
    )
    yield
    test_client.get("/logout")


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
