import pytest

from pycroft.lib.membership import change_membership_active_during 
from tests import factories as f


def test_user_change_membership(session, membership, processor, utcnow):
    change_membership_active_during(
        membership.id,
        begins_at=utcnow,
        ends_at=utcnow,
        processor=processor,
    )
    assert len(les := membership.user.log_entries) == 1
    log_entry = les[0]
    assert "Edited the membership" in log_entry.message


@pytest.fixture
def membership(module_session):
    m = f.MembershipFactory(group=f.PropertyGroupFactory())
    module_session.flush()
    return m
