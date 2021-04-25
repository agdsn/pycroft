from pycroft.lib.user import move, move_out, move_in
from pycroft.model import session
from tests import FactoryDataTestBase, ConfigFactory, UserFactory
from tests.factories import AddressFactory, RoomFactory


class UserRoomHistoryTestCase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()

        self.processor = UserFactory.create()

        self.user = UserFactory()
        self.user_no_room = UserFactory(room=None, address=AddressFactory())
        self.room = RoomFactory()

    def test_room_history_create(self):
        self.assertEqual(1, len(self.user.room_history_entries), "more than one room history entry")

        rhe = self.user.room_history_entries[0]

        self.assertEqual(self.user.room, rhe.room)
        self.assertIsNotNone(rhe.begins_at)
        self.assertIsNone(rhe.ends_at)

    def test_room_history_move(self):
        session.session.refresh(self.room)

        old_room = self.user.room

        move(self.user, self.room.building_id, self.room.level, self.room.number, self.processor)

        found_old = False
        found_new = False

        for rhe in self.user.room_history_entries:
            self.assertIsNotNone(rhe.begins_at)

            if rhe.room == old_room:
                self.assertIsNotNone(rhe.ends_at)
                found_old = True
            elif rhe.room == self.room:
                self.assertIsNone(rhe.ends_at)
                found_new = True

        self.assertTrue(found_new, "Did not find new history entry")
        self.assertTrue(found_old, "Did not find old history entry")

    def test_room_history_move_out(self):
        move_out(self.user, comment="test", processor=self.processor, when=session.utcnow())

        session.session.commit()

        rhe = self.user.room_history_entries[0]

        self.assertIsNotNone(rhe.begins_at)
        self.assertIsNotNone(rhe.ends_at)

    def test_room_history_move_in(self):
        self.assertEqual(0, len(self.user_no_room.room_history_entries))

        move_in(self.user_no_room, self.room.building.id, self.room.level, self.room.number,
                mac=None, processor=self.processor)

        session.session.commit()

        rhe = self.user_no_room.room_history_entries[0]

        self.assertEqual(rhe.room, self.room)

        self.assertIsNotNone(rhe.begins_at)
        self.assertIsNone(rhe.ends_at)
