from sqlalchemy.exc import IntegrityError

from pycroft.lib.facilities import create_room
from tests import FactoryDataTestBase, factories


class OneBuildingTestCase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.building = factories.BuildingFactory()
        self.processor = factories.UserFactory()
        self.address = factories.AddressFactory()

    def test_create_room(self):
        room = create_room(self.building, 1, "A1-01", self.processor, self.address)
        self.session.commit()
        self.assert_object_persistent(room)

    def test_create_room_needs_address(self):
        with self.assertRaises(IntegrityError):
            room = create_room(self.building, 1, "A1-01", self.processor, address=None)
