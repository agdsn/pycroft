from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.interval import closedopen, Interval, starting_from
from pycroft.helpers.utc import DateTimeTz
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

    @pytest.fixture
    def is_violator(self, session, user_to_block, config):
        def is_violator(when: Interval[DateTimeTz]) -> bool:
            return user_to_block.member_of(config.violation_group, when=when)

        return is_violator

    def test_deferred_blocking_and_unblocking_works(
        self, session, utcnow, user_to_block, config, is_violator
    ):
        u = user_to_block
        blockage, unblockage = (utcnow + timedelta(days=d) for d in (1, 3))
        assert not is_violator(when=closedopen(blockage, unblockage))

        # deferred blocking
        blocked_user = block(
            u, reason="test", processor=u, during=starting_from(blockage)
        )

        blocked_during = closedopen(blockage, unblockage)
        assert u.latest_log_entry.author == blocked_user
        assert is_violator(when=blocked_during)

        # deferred unblocking
        unblocked_user = unblock(blocked_user, processor=u, when=unblockage)

        assert unblocked_user.log_entries[0].author == unblocked_user
        assert unblocked_user.member_of(config.violation_group, when=blocked_during)
        assert not is_violator(when=starting_from(unblockage))
