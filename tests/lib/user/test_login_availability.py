import pytest

from pycroft.helpers.user import login_hash
from pycroft.lib.user import login_available, LoginTakenException, check_new_user_data_unused
from pycroft.model.unix_account import UnixTombstone


def test_login_reuse_present(session, processor):
    assert not login_available(processor.login, session)


LOGIN = "taken"


def test_tombstoned_login_not_available(session):
    assert not login_available(LOGIN, session)


def test_tombstoned_login_fails_check(session):
    with pytest.raises(LoginTakenException):
        check(LOGIN)


def test_existing_login_not_available(session, processor):
    assert not login_available(processor.login, session)


def test_existing_login_fails_check(session, processor):
    with pytest.raises(LoginTakenException):
        check(processor.login)


def test_unused_login_available(session):
    assert login_available(f"not-{LOGIN}", session)


def test_unused_login_passes_check(session):
    login = f"not-{LOGIN}"
    try:
        check(login)
    except LoginTakenException:
        pytest.fail(f"login {login!r} did not pass user data check")


def check(login: str):
    check_new_user_data_unused(login=login, email="unused@unused.com", swdd_person_id="9999999")


@pytest.fixture(scope="module", autouse=True)
def tombstone(module_session) -> UnixTombstone:
    ts = UnixTombstone(login_hash=login_hash(LOGIN))
    with module_session.begin_nested():
        module_session.add(ts)
    return ts
