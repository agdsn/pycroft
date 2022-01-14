import pytest
from sqlalchemy.future import select

from pycroft.model.facilities import Room
from tests import factories


@pytest.fixture(autouse=True)
def _session(session):
    return session


@pytest.fixture
def room():
    return factories.RoomFactory()


@pytest.fixture
def hans(room):
    return factories.UserFactory(room=room, name="Hans", address=room.address)


@pytest.fixture(autouse=True)
def other_inhabitant(session, room):
    return factories.UserFactory(room=room, name="Franz",
                                 address=factories.AddressFactory())


@pytest.fixture(autouse=True)
def other_room():
    return factories.RoomFactory.create()


def test_user_marked_as_inhabitant(hans):
    assert hans.room.users_sharing_address == [hans]


def test_users_sharing_address_expr(session, room, hans):
    assert session.scalars(
        select(Room)
            .where(Room.users_sharing_address.any())
    ).all() == [room]
