from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from pycroft import config
from pycroft.helpers.interval import closedopen
from pycroft.lib.user import block, unblock
from pycroft.model.config import Config
from pycroft.model.user import User
from tests import factories


@pytest.fixture(scope="module")
def config(module_session: Session) -> Config:
    return factories.ConfigFactory.create()

class TestUserBlockingAndUnblocking:
    @pytest.fixture(scope="class")
    def user_to_block(self, class_session, config) -> User:
        return factories.UserFactory.create(
            with_membership=True,
            membership__includes_today=True,
            membership__group=config.member_group,
        )

    @pytest.fixture(scope="class", autouse=True)
    def _sanity(self, user_to_block, config):
        assert config.violation_group not in user_to_block.active_property_groups()

    @staticmethod
    def assert_violation_membership(user, config, subinterval=None):
        if subinterval is None:
            assert not user.has_property("network_access")
            assert user.member_of(config.violation_group)
            return

        assert user.member_of(config.violation_group, when=subinterval)

    @staticmethod
    def assert_no_violation_membership(user, subinterval=None):
        if subinterval is None:
            assert user.has_property("network_access")
            assert not user.member_of(config.violation_group)
            return

        assert not user.member_of(config.violation_group, when=subinterval)

    def test_deferred_blocking_and_unblocking_works(self, session, utcnow, user_to_block, config):
        u = user_to_block

        blockage = utcnow + timedelta(days=1)
        unblockage = blockage + timedelta(days=2)
        blocked_user = block(u, reason="test", processor=u, during=closedopen(blockage, None))

        blocked_during = closedopen(blockage, unblockage)
        assert u.latest_log_entry.author == blocked_user
        self.assert_violation_membership(blocked_user, config, subinterval=blocked_during)

        unblocked_user = unblock(blocked_user, processor=u, when=unblockage)

        assert unblocked_user.log_entries[0].author == unblocked_user
        self.assert_violation_membership(unblocked_user, config, subinterval=blocked_during)
