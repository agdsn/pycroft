from datetime import datetime

from pycroft.lib.membership import change_membership_active_during 
from tests import FactoryDataTestBase
from tests.factories import UserFactory, MembershipFactory, PropertyGroupFactory

class TestMembershipChangeTestCase(FactoryDataTestBase):

    def create_factories(self):
        super().create_factories()
        self.admin = UserFactory()
        self.group = PropertyGroupFactory()
        self.membership = MembershipFactory(group=self.group)

    def test_user_change_membership(self):
        change_membership_active_during(self.membership.id, datetime.utcnow(), datetime.utcnow(), self.admin)
        #self.session.refresh()
        assert self.membership.user.log_entries != []
        log_entry = self.membership.user.log_entries[0]
        assert "Edited the membership" in log_entry.message
