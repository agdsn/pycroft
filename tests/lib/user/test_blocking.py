from datetime import timedelta

from pycroft import config
from pycroft.helpers.interval import closedopen
from pycroft.lib import user as UserHelper
from pycroft.model import session
from tests import FactoryWithConfigDataTestBase, factories


class UserWithNetworkAccessTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user_to_block = factories.user.UserWithMembershipFactory.create(
            membership__includes_today=True,
            membership__group=self.config.member_group,
        )
        self.assertNotIn(self.config.violation_group, self.user_to_block.active_property_groups())

    def assert_violation_membership(self, user, subinterval=None):
        if subinterval is None:
            self.assertFalse(user.has_property("network_access"))
            self.assertTrue(user.member_of(config.violation_group))
            return

        self.assertTrue(user.member_of(config.violation_group, when=subinterval))

    def assert_no_violation_membership(self, user, subinterval=None):
        if subinterval is None:
            self.assertTrue(user.has_property("network_access"))
            self.assertFalse(user.member_of(config.violation_group))
            return

        self.assertFalse(user.member_of(config.violation_group, when=subinterval))

    def test_deferred_blocking_and_unblocking_works(self):
        u = self.user_to_block

        blockage = session.utcnow() + timedelta(days=1)
        unblockage = blockage + timedelta(days=2)
        blocked_user = UserHelper.block(u, reason=u"test", processor=u,
                                        during=closedopen(blockage, None))
        session.session.commit()

        blocked_during = closedopen(blockage, unblockage)
        self.assertEqual(u.log_entries[0].author, blocked_user)
        self.assert_violation_membership(blocked_user, subinterval=blocked_during)

        unblocked_user = UserHelper.unblock(blocked_user, processor=u, when=unblockage)
        session.session.commit()

        self.assertEqual(unblocked_user.log_entries[0].author, unblocked_user)
        self.assert_violation_membership(unblocked_user, subinterval=blocked_during)