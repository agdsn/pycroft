from pycroft.lib.user import edit_address
from pycroft.model.user import User
from tests import FactoryDataTestBase

from ...factories import UserFactory, UserWithoutRoomFactory

class TestUserChangeAddressTestCase(FactoryDataTestBase):

    def create_factories(self):
        super().create_factories()
        self.admin = UserFactory()

    @property
    def address_args(self) -> dict[str]:
        return {
            'street': "Blahstraße",
            'number': "5",
            'addition': "Keller",
            'zip_code': "01217",
            'city': "Dresden",
            'state': None,
            'country': None,
        }

    # TODO with pytest, make this a parametrized test
    def assert_user_address_change(self, user: User, address_args: dict[str]):
        assert not user.has_custom_address

        edit_address(user, self.admin, **address_args)
        self.session.commit()

        self.session.refresh(user)
        if user.room:
            assert user.has_custom_address
        for key, val in self.address_args.items():
            if key == 'country':
                assert user.address.country == val or 'Germany'
                continue
            assert getattr(user.address, key) == (val or '')
        assert len(user.log_entries) > 0
        log_entry = user.log_entries[-1]
        assert log_entry.author == self.admin

    def test_plain_user_address_add(self):
        self.assert_user_address_change(UserWithoutRoomFactory(), self.address_args)

    def test_user_with_room_different_address(self):
        self.assert_user_address_change(UserFactory(), self.address_args)
