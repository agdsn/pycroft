from datetime import datetime, timedelta

import pytest

from pycroft.lib import user as lib_user
from pycroft.model.facilities import Room
from pycroft.model.task import Task, TaskStatus, TaskType, UserTask
from pycroft.model.task_serialization import UserMoveInParams
from pycroft.model.user import User
from tests import factories
from tests.assertions import assert_one
from . import ExampleUserData
from .task_helpers import create_task_and_execute
from .assertions import assert_mail_reasonable


@pytest.fixture(scope="module")
def room(module_session) -> Room:
    return factories.RoomFactory(level=1, number="1", patched_with_subnet=True)


@pytest.fixture(scope="module")
def user(module_session, config, room) -> User:
    return factories.UserFactory(
        with_membership=True,
        membership__group=config.member_group,
        room=None,
        address=room.address,
        birthdate=datetime.fromisoformat("2000-01-01"),
    )


@pytest.fixture(scope="session")
def mac() -> str:
    return "12:11:11:11:11:11"


class TestUserMoveIn:
    @pytest.fixture(scope="class")
    def user_data(self):
        return ExampleUserData

    def test_move_in(self, session, user, room, processor, config, mac, mail_capture):
        lib_user.move_in(
            user,
            building_id=room.building.id,
            level=1,
            room_number="1",
            mac=mac,
            processor=processor,
        )

        assert user.room == room
        assert user.address == user.room.address

        user_interface = assert_one(assert_one(user.hosts).interfaces)
        assert user_interface.mac == mac
        assert_one(user_interface.ips)

        # checks the initial group memberships
        active_user_groups = user.active_property_groups()
        for group in {config.member_group, config.network_access_group}:
            assert group in active_user_groups

        assert not user.has_property("reduced_membership_fee")
        assert_mail_reasonable(assert_one(mail_capture), subject_re="Wohnortänderung")

    def test_move_in_scheduling(self, session, utcnow, user, room, processor, config, mail_capture):
        processing_user = processor
        test_mac = '00:de:ad:be:ef:00'
        lib_user.move_in(
            user,
            building_id=room.building.id,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=processing_user,
            when=utcnow + timedelta(days=1),
        )
        assert (task := Task.q.first()) is not None
        assert task.parameters == UserMoveInParams(
            building_id=room.building.id,
            level=1,
            room_number="1",
            mac=test_mac,
        )
        assert not mail_capture


class TestMoveInImpl:
    def test_successful_move_in_execution_without_mac(self, session, user, room, mail_capture):
        task = create_task_and_execute(
            TaskType.USER_MOVE_IN,
            user,
            {
                "level": room.level,
                "building_id": room.building_id,
                "room_number": room.number,
            },
        )
        assert isinstance(task, UserTask)
        assert_successful_move_in_execution(task, room)
        assert_mail_reasonable(assert_one(mail_capture), subject_re="Wohnortänderung")
        assert not user.hosts

    def test_successful_move_in_execution_minimal(self, session, user, room, mac, mail_capture):
        task = create_task_and_execute(
            TaskType.USER_MOVE_IN,
            user,
            {
                "mac": mac,
                "level": room.level,
                "building_id": room.building_id,
                "room_number": room.number,
            },
        )
        assert isinstance(task, UserTask)
        assert_successful_move_in_execution(task, room)
        interface = assert_one(assert_one(user.hosts).interfaces)
        assert interface.mac == mac
        assert_mail_reasonable(assert_one(mail_capture), subject_re="Wohnortänderung")


def assert_successful_move_in_execution(task: UserTask, room: Room):
    assert task.status == TaskStatus.EXECUTED
    assert task.user.room == room


def assert_failing_move_execution(task: UserTask, error_needle: str):
    assert task.status == TaskStatus.FAILED
    assert error_needle in assert_one(task.errors).lower()
    assert task.user.room is None
