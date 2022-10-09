import typing as t

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pycroft.lib.address import get_or_create_address
from pycroft.lib.facilities import create_room, edit_room
from pycroft.model.address import Address
from pycroft.model.facilities import Building, Room
from pycroft.model.user import User
from tests import factories


@pytest.fixture(scope="module")
def processor(module_session: Session) -> User:
    return factories.UserFactory.create(without_room=True)

class TestCreateRoom:
    @pytest.fixture(scope="class")
    def building(self, class_session: Session) -> Building:
        return factories.BuildingFactory.create()

    @pytest.fixture(scope="class")
    def address(self, class_session: Session) -> Address:
        return factories.AddressFactory.create()

    def test_create_room(
        self, session: Session, building: Building, processor: User, address: Address
    ) -> None:
        room = create_room(building, 1, "A1-01", processor, address)
        session.flush()
        assert inspect(room).persistent

    def test_create_room_needs_address(
        self, session: Session, building: Building, processor: User
    ):
        with pytest.raises(IntegrityError):
            create_room(building, 1, "A1-01", processor, address=t.cast(Address, None))


class TestRoomEdit:
    @pytest.fixture(scope="class")
    def room(self, class_session: Session) -> Room:
        return factories.RoomFactory.create()

    @pytest.fixture(scope="class", autouse=True)
    def other_fixtures(self, class_session: Session, room):
        factories.UserFactory.create_batch(3, room=room)

    def test_change_number_and_address(
        self, session: Session, room: Room, processor: User
    ):
        new_address = get_or_create_address(
            street="Wundtstraße",
            number="5",
            addition="Keller",
            zip_code="01217",
            city="Dresden",
        )
        edit_room(
            room,
            "new number",
            room.inhabitable,
            room.swdd_vo_suchname,
            new_address,
            processor,
        )
