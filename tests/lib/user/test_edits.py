import pytest

from pycroft.lib import user as lib_user
from pycroft.model.user import User
from tests.factories import UserFactory


@pytest.fixture(scope="module")
def user(module_session) -> User:
    return UserFactory.create()


def test_correct_new_name(user):
    new_name = "A new name"
    assert new_name != user.name
    lib_user.edit_name(user, new_name, user)
    assert user.name == new_name


def test_correct_new_email(user):
    new_mail = "user@example.net"
    assert new_mail != user.email
    lib_user.edit_email(user, new_mail, False, user)
    assert user.email == new_mail
