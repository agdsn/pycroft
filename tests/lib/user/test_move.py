from datetime import timedelta

import pytest

from pycroft.lib import user as lib_user
from pycroft.model.facilities import Room
from pycroft.model.task import Task, UserTask, TaskStatus, TaskType
from pycroft.model.task_serialization import UserMoveParams
from pycroft.model.user import User
from tests import factories
from tests.assertions import assert_unchanged
from tests.factories import UserFactory, RoomFactory
from tests.lib.user.task_helpers import create_task_and_execute


class TestUserMove:
    @pytest.fixture(scope="class")
    def subnet(self, class_session):
        return factories.SubnetFactory.create()

    @pytest.fixture(scope="class")
    def user(self, class_session, subnet) -> User:
        return factories.UserFactory(
            with_host=True,
            room__patched_with_subnet=True,
            room__patch_ports__switch_port__default_vlans__subnets=[subnet]
        )

    @pytest.fixture(scope="class")
    def new_room_other_building(self, class_session) -> Room:
        return factories.RoomFactory(patched_with_subnet=True)

    @pytest.fixture(scope="class")
    def new_room_same_building(self, class_session, user, subnet) -> Room:
        return factories.RoomFactory(
            building=user.building,
            patched_with_subnet=True,
            patch_ports__switch_port__default_vlans__subnets=[subnet],
        )

    def test_move_scheduling(
        self, session, utcnow, user, processor, new_room_other_building
    ):
        when = utcnow + timedelta(days=1)
        lib_user.move(
            user,
            building_id=new_room_other_building.building.id,
            level=new_room_other_building.level,
            room_number=new_room_other_building.number,
            processor=processor,
            when=when,
        )
        tasks = session.query(Task).all()
        assert len(tasks) == 1
        [task] = tasks
        assert isinstance(task, UserTask)
        assert task.user == user
        assert task.parameters == UserMoveParams(
            building_id=new_room_other_building.building.id,
            level=new_room_other_building.level,
            room_number=new_room_other_building.number,
        )

    def test_moves_into_same_room(self, session, user, processor):
        old_room = user.room
        with pytest.raises(AssertionError):
            lib_user.move(
                user, old_room.building.id, old_room.level, old_room.number, processor
            )

    def test_moves_into_other_building(
        self, session, user, processor, new_room_other_building
    ):
        lib_user.move(
            user,
            new_room_other_building.building.id,
            new_room_other_building.level,
            new_room_other_building.number,
            processor,
        )
        assert user.room == new_room_other_building
        assert user.hosts[0].room == new_room_other_building
        # TODO test for changing ip


class TestMoveImpl:
    # TODO move into own module and then use module-scoped fixtures and class inheritance
    @pytest.fixture(scope="class")
    def user(self, class_session, config) -> User:
        return UserFactory.create(
            with_membership=True,
            membership__group=config.member_group,
            with_host=True,
        )

    @pytest.fixture(scope="class")
    def old_room(self, user):
        return user.room

    @pytest.fixture(scope="class")
    def new_room(self, class_session) -> Room:
        return RoomFactory.create()

    def test_successful_move_execution(self, session, user, new_room):
        params = {
            "level": new_room.level,
            "building_id": new_room.building_id,
            "room_number": new_room.number,
        }
        task = create_task_and_execute(TaskType.USER_MOVE, user, params)
        assert task.status == TaskStatus.EXECUTED
        assert user.room == new_room

    def test_move_execution_without_level_fails(self, session, user, new_room):
        params = {
            "building_id": new_room.building_id,
            "room_number": new_room.number,
        }
        with assert_unchanged(lambda: user.room):
            task = create_task_and_execute(TaskType.USER_MOVE, user, params)
        self.assert_failing_move_execution(task, error_needle="level")

    def test_move_execution_without_building_id_fails(self, session, user, new_room):
        param = {
            "level": new_room.level,
            "room_number": new_room.number,
        }
        with assert_unchanged(lambda: user.room):
            task = create_task_and_execute(TaskType.USER_MOVE, user, param)
        self.assert_failing_move_execution(task, error_needle="building_id")

    def test_move_execution_without_room_number_fails(self, session, user, new_room):
        params = {
            "level": new_room.level,
            "building_id": new_room.building_id,
        }
        with assert_unchanged(lambda: user.room):
            task = create_task_and_execute(TaskType.USER_MOVE, user, params)
        self.assert_failing_move_execution(task, error_needle="room_number")

    @staticmethod
    def assert_failing_move_execution(task: Task, error_needle: str):
        assert task.status == TaskStatus.FAILED
        assert len(task.errors) == 1
        [error] = task.errors
        assert error_needle in error.lower()
