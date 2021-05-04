import pytest
from sqlalchemy.orm import close_all_sessions, scoped_session, sessionmaker

from pycroft.model import session as pyc_session
from web import make_app

from .. import teardown, setup, get_engine_and_connection


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
def session(connection, request):
    transaction = connection.begin_nested()
    request.addfinalizer(lambda: rollback(transaction))
    s = scoped_session(sessionmaker(bind=connection))
    pyc_session.set_scoped_session(s)
    return s


@pytest.fixture(scope='session')
def app():
    return make_app()
