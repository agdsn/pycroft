from pycroft.lib import user as UserHelper
from tests.factories import UserFactory
from tests.legacy_base import FactoryDataTestBase


class UserEditsTestCase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = UserFactory()

    def test_correct_new_name(self):
        new_name = "A new name"
        assert new_name != self.user.name
        UserHelper.edit_name(self.user, new_name, self.user)
        assert self.user.name == new_name

    def test_correct_new_email(self):
        new_mail = "user@example.net"
        assert new_mail != self.user.email
        UserHelper.edit_email(self.user, new_mail, False, self.user)
        assert self.user.email == new_mail
