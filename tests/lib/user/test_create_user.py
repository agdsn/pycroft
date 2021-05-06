from pycroft.lib import user as UserHelper
from tests import FactoryDataTestBase, factories, UserFactory
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
        self.assertEqual(new_user.name, self.user.name)
        self.assertEqual(new_user.login, self.user.login)
        self.assertEqual(new_user.email, self.user.email)
        # TODO fix signature and check for explicitly supplied address.
        # self.assertEqual(new_user.address, config.dummy_address)
        assert_account_name(new_user.account, f"User {new_user.id}")
        assert_membership_groups(new_user.active_memberships(), [self.config.member_group])
        self.assertEqual(new_user.unix_account.home_directory, f"/home/{new_user.login}")
        self.assertEqual(len(new_user.log_entries), 2)
        first, second = new_user.log_entries
        assert_logmessage_startswith(first, "Added to group Mitglied")
        assert_logmessage_startswith(second, "User created")
        assert new_user.account is not None
        assert new_user.account.balance == 0