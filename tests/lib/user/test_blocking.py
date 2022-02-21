from datetime import timedelta

from pycroft import config
from pycroft.helpers.interval import closedopen
from pycroft.lib import user as UserHelper
from pycroft.model import session
from tests import factories
from tests.legacy_base import FactoryWithConfigDataTestBase


class UserWithNetworkAccessTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user_to_block = factories.user.UserFactory.create(
            with_membership=True,
            membership__includes_today=True,
            membership__group=self.config.member_group,
        )
        assert self.config.violation_group \
          not in self.user_to_block.active_property_groups()

    def assert_violation_membership(self, user, subinterval=None):
        if subinterval is None:
            assert not user.has_property("network_access")
            assert user.member_of(config.violation_group)
            return

        self.assertTrue(user.member_of(config.violation_group, when=subinterval))

    def assert_no_violation_membership(self, user, subinterval=None):
        if subinterval is None:
            assert user.has_property("network_access")
            assert not user.member_of(config.violation_group)
            return

        assert not user.member_of(config.violation_group, when=subinterval)

    def test_deferred_blocking_and_unblocking_works(self):
        u = self.user_to_block

        blockage = session.utcnow() + timedelta(days=1)
        unblockage = blockage + timedelta(days=2)
        blocked_user = UserHelper.block(u, reason="test", processor=u,
                                        during=closedopen(blockage, None))
        session.session.commit()

        blocked_during = closedopen(blockage, unblockage)
        assert u.log_entries[0].author == blocked_user
        self.assert_violation_membership(blocked_user, subinterval=blocked_during)

        unblocked_user = UserHelper.unblock(blocked_user, processor=u, when=unblockage)
        session.session.commit()

        assert unblocked_user.log_entries[0].author == unblocked_user
        self.assert_violation_membership(unblocked_user, subinterval=blocked_during)
