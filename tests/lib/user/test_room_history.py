from pycroft.lib.user import move, move_out, move_in
from pycroft.model import session
from pycroft.model.user import RoomHistoryEntry
from tests.legacy_base import FactoryDataTestBase
from tests.factories import AddressFactory, RoomFactory, ConfigFactory, UserFactory


class UserRoomHistoryTestCase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()

        self.processor = UserFactory.create()

        self.user = UserFactory()
        self.user_no_room = UserFactory(room=None, address=AddressFactory())
        self.room = RoomFactory()

    def test_room_history_create(self):
        assert 1 == len(self.user.room_history_entries), "more than one room history entry"

        rhe: RoomHistoryEntry = self.user.room_history_entries[0]

        assert self.user.room == rhe.room
        assert rhe.active_during.begin is not None
        assert rhe.active_during.end is None

    def test_room_history_move(self):
        session.session.refresh(self.room)

        old_room = self.user.room

        move(self.user, self.room.building_id, self.room.level, self.room.number, self.processor)

        found_old = False
        found_new = False

        for rhe in self.user.room_history_entries:
            assert rhe.active_during.begin is not None

            if rhe.room == old_room:
                assert rhe.active_during.end is not None
                found_old = True
            elif rhe.room == self.room:
                assert rhe.active_during.end is None
                found_new = True

        assert found_new, "Did not find new history entry"
        assert found_old, "Did not find old history entry"

    def test_room_history_move_out(self):
        move_out(self.user, comment="test", processor=self.processor, when=session.utcnow())

        session.session.commit()

        rhe = self.user.room_history_entries[0]

        assert rhe.active_during.begin  is not None
        assert rhe.active_during.end is not None

    def test_room_history_move_in(self):
        assert 0 == len(self.user_no_room.room_history_entries)

        move_in(self.user_no_room, self.room.building.id, self.room.level, self.room.number,
                mac=None, processor=self.processor)

        session.session.commit()

        rhe = self.user_no_room.room_history_entries[0]

        assert rhe.room == self.room

        assert rhe.active_during.begin is not None
        assert rhe.active_during.end is None
