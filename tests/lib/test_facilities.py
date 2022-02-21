from sqlalchemy.exc import IntegrityError

from pycroft.lib.address import get_or_create_address
from pycroft.lib.facilities import create_room, edit_room
from tests import factories
from tests.legacy_base import FactoryDataTestBase


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


class RoomEditTestCase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.room = factories.RoomFactory()
        factories.UserFactory.create_batch(3, room=self.room)
        self.processor = factories.UserFactory(without_room=True)

    def test_change_number_and_address(self):
        new_address = get_or_create_address(street='Wundtstraße', number='5', addition='Keller',
                              zip_code='01217', city='Dresden')
        edit_room(self.room, 'new number', self.room.inhabitable, self.room.swdd_vo_suchname,
                  new_address, self.processor)
