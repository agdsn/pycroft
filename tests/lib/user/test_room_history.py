import pytest

from pycroft.lib.user import move, move_out, move_in
from pycroft.model.facilities import Room
from pycroft.model.user import RoomHistoryEntry, User
from tests.assertions import assert_one
from tests.factories import AddressFactory, RoomFactory, UserFactory


@pytest.fixture(scope="module")
def user(module_session) -> User:
    return UserFactory()


@pytest.fixture(scope="module")
def user_no_room(module_session) -> User:
    return UserFactory.create(room=None, address=AddressFactory())


@pytest.fixture(scope="module")
def room(module_session) -> Room:
    return RoomFactory()


@pytest.mark.usefixtures("config", "session")
class TestUserRoomHistory:
    def test_room_history_create(self, session, user):
        rhe: RoomHistoryEntry = assert_one(user.room_history_entries)
        assert user.room == rhe.room
        assert rhe.active_during.begin is not None
        assert rhe.active_during.end is None

    def test_room_history_move(self, session, user, processor, room):
        old_room = user.room
        assert old_room != room
        move(user, room.building_id, room.level, room.number, processor)
        session.refresh(user)

        rhes = user.room_history_entries
        old = [rhe for rhe in rhes if rhe.room == old_room]
        assert old, "Did not find old history entry"
        for rhe in old:
            assert rhe.active_during.begin is not None
            assert rhe.active_during.end is not None

        new = [rhe for rhe in rhes if rhe.room == room]
        assert new, "Did not find new history entry"
        for rhe in new:
            assert rhe.active_during.begin is not None
            assert rhe.active_during.end is None

    def test_room_history_move_out(self, session, user, processor, utcnow):
        move_out(user, comment="test", processor=processor, when=utcnow)
        session.refresh(user)

        rhe = user.room_history_entries[0]
        assert rhe.active_during.begin is not None
        assert rhe.active_during.end is not None

    def test_room_history_move_in(self, session, user_no_room, processor, room):
        assert user_no_room.room_history_entries == []

        move_in(
            user_no_room,
            room.building.id,
            room.level,
            room.number,
            mac=None,
            processor=processor,
        )
        session.refresh(user_no_room)

        rhe = user_no_room.room_history_entries[0]
        assert rhe.room == room
        assert rhe.active_during.begin is not None
        assert rhe.active_during.end is None
