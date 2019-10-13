from pycroft.helpers.i18n import localized

from pycroft.lib.facilities import create_room
from pycroft.model.logging import RoomLogEntry
from tests import FactoryDataTestBase, AdminMixin
from tests.factories import BuildingFactory
from tests.factories.address import AddressFactory


class RoomCreationTestCase(AdminMixin, FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.building = BuildingFactory.create()
        self.address = AddressFactory.create()

    def test_room_create(self):
        # act
        room = create_room(self.building, level=1, number="32b", processor=self.admin,
                           address=self.address)

        # assert
        self.session.refresh(self.building)
        self.assertEqual(self.building.rooms, [room])
        self.assertEqual(len(room.log_entries),1)
        l: RoomLogEntry = room.log_entries[0]
        self.assertEqual(l.author, self.admin)
        self.assertEqual(localized(l.message), "Room created.")
