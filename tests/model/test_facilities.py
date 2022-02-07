import pytest
from sqlalchemy.future import select

from pycroft.model.facilities import Room
from tests import factories


@pytest.fixture(scope='module')
def room(module_session):
    return factories.RoomFactory()


@pytest.fixture(scope='module')
def hans(module_session, room):
    return factories.UserFactory(room=room, name="Hans", address=room.address)


@pytest.fixture(scope='module', autouse=True)
def other_inhabitant(module_session, room):
    return factories.UserFactory(room=room, name="Franz",
                                 address=factories.AddressFactory())


@pytest.fixture(scope='module', autouse=True)
def other_room(module_session):
    return factories.RoomFactory.create()


def test_user_marked_as_inhabitant(session, hans):
    assert hans.room.users_sharing_address == [hans]


def test_users_sharing_address_expr(session, room, hans):
    assert session.scalars(
        select(Room).where(Room.users_sharing_address.any())
    ).all() == [room]
