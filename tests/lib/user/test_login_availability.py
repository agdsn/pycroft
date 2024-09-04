import pytest

from pycroft.helpers.user import login_hash
from pycroft.lib.user import login_available
from pycroft.model.unix_account import UnixTombstone


def test_login_reuse_present(session, processor):
    assert not login_available(processor.login, session)


LOGIN = "taken"


def test_login_reuse_past(session, tombstone):
    assert not login_available(LOGIN, session)
    assert login_available(f"not-{LOGIN}", session)


@pytest.fixture(scope="module")
def tombstone(module_session) -> UnixTombstone:
    ts = UnixTombstone(login_hash=login_hash(LOGIN))
    with module_session.begin_nested():
        module_session.add(ts)
    return ts
