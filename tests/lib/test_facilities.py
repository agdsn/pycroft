from typing import List

from pycroft.helpers.i18n import localized
from pycroft.lib.facilities import create_room, edit_room, get_room, \
    get_overcrowded_rooms
from pycroft.model.facilities import Room
from pycroft.model.logging import RoomLogEntry

from .. import FactoryDataTestBase, AdminMixin, UserFactory
from ..assertions import AssertionMixin
from ..factories import BuildingFactory, RoomFactory, UserWithHostFactory, \
    HostFactory
from ..factories.address import AddressFactory


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
        self.assertEqual(len(room.log_entries), 1)
        l: RoomLogEntry = room.log_entries[0]
        self.assertEqual(l.author, self.admin)
        self.assertEqual(localized(l.message), "Room created.")


class CreatedRoomTestCase(AdminMixin, AssertionMixin, FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.room = RoomFactory.create(level=1, number="1A")

    def test_room_edit(self):
        new_number = self.room.number + "_left"

        # act
        edit_room(self.room, new_number, inhabitable=False, processor=self.admin)

        # assert
        updated_room: Room = Room.q.get(self.room.id)
        self.assertEquals(updated_room.address, self.room.address)
        self.assertEquals(updated_room.number, new_number)
        self.assertEquals(updated_room.inhabitable, False)

        entries: List[RoomLogEntry] = updated_room.log_entries
        with self.assert_list_items(entries, 2) as (renamed, changed):
            self.assertRegexpMatches(localized(renamed.message), "Renamed room from .* to .*")
            self.assertRegexpMatches(localized(changed.message), "Changed inhabitable status")

    def test_room_get(self):
        room = get_room(self.room.building.id, level=1, room_number="1A")

        self.assertEqual(room, self.room)

    def test_overcrowded_room_is_reported(self):
        # arrange
        inhabitants = UserWithHostFactory.create_batch(3, room=self.room, host__room=self.room)
        other_dudes = UserFactory.create_batch(3, room=self.room)

        self.session.refresh(self.room)
        self.assertEqual(set(self.room.users), set(inhabitants) | set(other_dudes))

        # act
        crowds = get_overcrowded_rooms(self.room.building.id)

        # assert
        with self.assert_dict_items(crowds, expected_keys=self.room.id) as room_crowd:
            self.assertEqual(len(room_crowd), len(inhabitants))
            self.assertEqual(set(room_crowd), set(inhabitants))

    def test_room_overcrowded_with_multiple_hosts(self):
        # arrange
        hans, franz = UserFactory.create_batch(2, room=self.room)
        inhabitants = [hans, franz]
        HostFactory.create_batch(3, owner=hans, room=self.room)
        HostFactory.create_batch(3, owner=franz, room=self.room)

        # act
        crowds = get_overcrowded_rooms(self.room.building.id)

        # assert
        with self.assert_dict_items(crowds, expected_keys=self.room.id) as room_crowd:
            self.assertEqual(len(room_crowd), len(inhabitants))
            self.assertEqual(set(room_crowd), set(inhabitants))

    def test_room_not_overcrowded_with_one_guy_multiple_hosts_and_another_none(self):
        # arrange
        UserWithHostFactory.create(room=self.room, host__room=self.room)
        HostFactory.create_batch(3, owner=(UserFactory.create(room=self.room)))

        # act
        crowds = get_overcrowded_rooms(self.room.building_id)

        # assert
        self.assertFalse(crowds)
