from pycroft.lib import user as UserHelper
from tests import FactoryDataTestBase, UserFactory


class UserEditsTestCase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = UserFactory()

    def test_correct_new_name(self):
        new_name = "A new name"
        self.assertNotEqual(new_name, self.user.name)
        UserHelper.edit_name(self.user, new_name, self.user)
        self.assertEqual(self.user.name, new_name)

    def test_correct_new_email(self):
        new_mail = "user@example.net"
        self.assertNotEqual(new_mail, self.user.email)
        UserHelper.edit_email(self.user, new_mail, False, self.user)
        self.assertEqual(self.user.email, new_mail)
