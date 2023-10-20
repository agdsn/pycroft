import pytest
from datetime import datetime, timedelta

from pycroft.helpers.interval import closedopen
from pycroft.lib.user import get_active_users
from pycroft.model.user import PropertyGroup, User
from tests import factories as f


@pytest.fixture(scope="session")
def yesterday() -> datetime:
    return datetime.now() - timedelta(days=1)


@pytest.fixture(scope="session")
def next_year() -> datetime:
    return datetime.now() + timedelta(days=365)


@pytest.fixture(scope="module")
def g(module_session) -> PropertyGroup:
    return f.PropertyGroupFactory.create(name="cool group")


@pytest.fixture(scope="module")
def users_with_mem(module_session, yesterday, next_year, g) -> tuple[User, User]:
    u1 = f.UserFactory.create(
        with_membership=True,
        membership__group=g,
        membership__active_during=closedopen(yesterday, next_year),
    )
    u2 = f.UserFactory.create(
        with_membership=True,
        membership__group=g,
        membership__active_during=closedopen(yesterday, None),
    )
    return u1, u2


@pytest.fixture(scope="module")
def users_without_mem(module_session, yesterday, g) -> tuple[User, User]:
    u3 = f.UserFactory.create(
        with_membership=True,
        membership__group=g,
        membership__active_during=closedopen(None, yesterday),
    )
    u4 = f.UserFactory.create()
    return u3, u4


def test_get_active_members(session, g, users_with_mem):
    assert set(get_active_users(session, g)) == set(users_with_mem)
