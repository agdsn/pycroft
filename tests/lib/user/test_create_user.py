from pycroft.lib import user as UserHelper
from tests import factories
from tests.factories import UserFactory
from ...legacy_base import FactoryDataTestBase
from . import ExampleUserData
from .assertions import assert_account_name, assert_membership_groups, assert_logmessage_startswith


class UserCreationTest(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.config = factories.ConfigFactory()
        self.room = factories.RoomFactory(level=1, number="1", patched_with_subnet=True)
        self.processing_user = UserFactory()

    user = ExampleUserData

    def test_user_create(self):
        # needs: new_user, self.user (the initiating data),
        # self.config.member_group
        new_user, _ = UserHelper.create_user(
            self.user.name,
            self.user.login,
            self.user.email,
            self.user.birthdate,
            processor=self.processing_user,
            groups=[self.config.member_group],
            address=self.room.address,
        )
        assert new_user.name == self.user.name
        assert new_user.login == self.user.login
        assert new_user.email == self.user.email
        # TODO fix signature and check for explicitly supplied address.
        # assert new_user.address == config.dummy_address
        assert_account_name(new_user.account, f"User {new_user.id}")
        assert_membership_groups(new_user.active_memberships(), [self.config.member_group])
        assert new_user.unix_account.home_directory == f"/home/{new_user.login}"
        assert len(new_user.log_entries) == 2
        first, second = new_user.log_entries
        assert_logmessage_startswith(first, "Added to group Mitglied")
        assert_logmessage_startswith(second, "User created")
        assert new_user.account is not None
        assert new_user.account.balance == 0
