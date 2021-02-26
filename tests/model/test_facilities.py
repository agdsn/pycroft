from pycroft.model.facilities import Room
from tests import FactoryDataTestBase, factories


class TestRoomUsersWithSameAddress(FactoryDataTestBase):

    def create_factories(self):
        super().create_factories()
        address = factories.AddressFactory()
        self.room = factories.RoomFactory(address=address)

        self.hans = factories.UserFactory(room=self.room, name="Hans", address=address)
        self.franz = factories.UserFactory(room=self.room, name="Franz",
                                           address=factories.AddressFactory())

    def test_users_with_same_address(self):
        assert self.room.users_sharing_address == [self.hans]

    def test_users_with_same_address_expr(self):
        assert Room.q.filter(Room.users_sharing_address.any()).all() == [self.room]
