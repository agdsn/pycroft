import typing as t
from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.interval import open
from pycroft.lib import user as lib_user
from pycroft.model.address import Address
from pycroft.model.facilities import Room
from pycroft.model.task import Task, TaskType, TaskStatus
from pycroft.model.task_serialization import UserMoveOutParams
from pycroft.model.user import User
from tests.assertions import assert_unchanged, assert_one
from tests.factories import RoomFactory, AddressFactory, UserFactory
from tests.lib.user.task_helpers import create_task_and_execute

@pytest.fixture(scope="module")
def user(module_session, config):
    return UserFactory.create(
        with_host=True,
        with_membership=True,
        membership__group=config.member_group,
    )


class TestMovedInUser:
    @pytest.fixture(scope="class")
    def other_room(self, class_session) -> Room:
        return RoomFactory.create()

    @pytest.fixture
    def move_out(
        self, session, processor, utcnow
    ) -> t.Callable[[User, str | None], None]:
        def move_out(user: User, comment: str | None = None) -> None:
            lib_user.move_out(
                user, comment=comment or "", processor=processor, when=utcnow
            )
            session.refresh(user)

        return move_out

    @pytest.fixture
    def customize_address(self, session: Session) -> t.Callable[[User], Address]:
        def customize_address(user: User) -> Address:
            user.address = address = AddressFactory.create(city="Bielefeld")
            session.add(user)
            session.flush()
            assert user.has_custom_address
            return address

        return customize_address

    def test_move_out_keeps_address(self, session, user, utcnow, move_out):
        assert not user.has_custom_address
        with assert_unchanged(lambda: user.address):
            move_out(user, "")
        assert user.active_memberships(when=open(utcnow, None)) == []
        assert user.room is None

    def test_move_out_keeps_custom_address(self, user, customize_address, move_out):
        address = customize_address(user)
        move_out(user, "")
        assert user.address == address

    @pytest.fixture
    def move(self, session, processor) -> t.Callable[[User, Room], None]:
        def move(user, room):
            lib_user.move(
                user,
                processor=processor,
                building_id=room.building_id,
                level=room.level,
                room_number=room.number,
            )
            session.refresh(user)

        return move

    def test_move_changes_address(self, move, user, other_room):
        move(user, other_room)
        assert user.address == other_room.address

    def test_move_keeps_custom_address(self, customize_address, move, user, other_room):
        address = customize_address(user)
        move(user, other_room)
        assert user.address == address

    @pytest.mark.parametrize("end_membership", (True, False))
    def test_move_out_gets_scheduled(
        self, end_membership, user, processor, session, utcnow
    ):
        old_room = user.room
        lib_user.move_out(
            user,
            comment="",
            processor=processor,
            when=utcnow + timedelta(days=1),
            end_membership=end_membership,
        )
        assert user.room == old_room
        task = assert_one(session.query(Task).all())
        assert task.type == TaskType.USER_MOVE_OUT
        assert task.parameters == UserMoveOutParams(
            comment="", end_membership=end_membership
        )


class TestMoveOutImpl:
    @pytest.mark.parametrize(
        "params",
        (
            {"comment": "Kommentar", "end_membership": True},
            {"comment": "", "end_membership": True},
        ),
    )
    def test_move_out_success(self, session, user, utcnow, params: dict):
        task = create_task_and_execute(TaskType.USER_MOVE_OUT, user, params)
        session.refresh(user)

        assert task.status == TaskStatus.EXECUTED
        assert user.room is None
        relevant_interval = open(utcnow + timedelta(seconds=1), None)
        assert user.active_memberships(when=relevant_interval) == []

    @pytest.mark.parametrize(
        "params, error_needle",
        (
            ({"comment": ""}, "end_membership"),
            ({"end_membership": True}, "comment"),
        ),
    )
    def test_move_out_bad_params(
        self, session, user, utcnow, params: dict, error_needle: str
    ):
        task = create_task_and_execute(TaskType.USER_MOVE_OUT, user, params)
        session.refresh(user)

        assert task.status == TaskStatus.FAILED
        assert error_needle in assert_one(task.errors).lower()
        assert user.room is not None
