from datetime import datetime, timedelta

from pycroft.lib import user as UserHelper
from pycroft.model import session
from pycroft.model.task import Task, TaskStatus, TaskType
from pycroft.model.task_serialization import UserMoveInParams
from tests import factories, UserFactory
from ...legacy_base import FactoryDataTestBase, FactoryWithConfigDataTestBase
from . import ExampleUserData
from .task_helpers import create_task_and_execute


class Test_User_Move_In(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.config = factories.ConfigFactory()
        self.room = factories.RoomFactory(level=1, number="1", patched_with_subnet=True)
        self.processing_user = UserFactory()
        self.user = UserFactory(
            with_membership=True,
            membership__group=self.config.member_group,
            room=None,
            address=self.room.address,
            birthdate=datetime.fromisoformat('2000-01-01')
        )

    user = ExampleUserData

    def create_some_user(self):
        new_user, _ = UserHelper.create_user(
            self.user.name,
            self.user.login,
            self.user.email,
            self.user.birthdate,
            processor=self.processing_user,
            groups=[self.config.member_group],
            address=self.room.address,
        )
        return new_user

    def test_0010_move_in(self):
        test_mac = "12:11:11:11:11:11"

        UserHelper.move_in(
            self.user,
            building_id=self.room.building.id,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
        )

        assert self.user.room == self.room
        assert self.user.address == self.user.room.address

        assert len(self.user.hosts) == 1
        [user_host] = self.user.hosts
        assert len(user_host.interfaces) == 1
        user_interface = user_host.interfaces[0]
        assert len(user_interface.ips) == 1
        assert user_interface.mac == test_mac

        # checks the initial group memberships
        active_user_groups = self.user.active_property_groups()
        for group in {self.config.member_group, self.config.network_access_group}:
            assert group in active_user_groups

        assert not self.user.has_property("reduced_membership_fee")

    def test_move_in_scheduling(self):
        test_mac = '00:de:ad:be:ef:00'
        UserHelper.move_in(
            self.user,
            building_id=self.room.building.id,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            when=session.utcnow() + timedelta(days=1),
        )
        assert (task := Task.q.first()) is not None
        assert task.parameters == UserMoveInParams(
            building_id=self.room.building.id,
            level=1,
            room_number="1",
            mac=test_mac,
        )


class TestMoveInImpl(FactoryWithConfigDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.room = factories.RoomFactory(level=1, number="1", patched_with_subnet=True)
        self.processing_user = UserFactory()
        self.user = UserFactory(
            with_membership=True,
            membership__group=self.config.member_group,
            room=None,
            address=self.room.address,
            birthdate=datetime.fromisoformat('2000-01-01')
        )
        self.mac = '00:de:ad:be:ef:00'

    def test_successful_move_in_execution_without_mac(self):
        self.assert_successful_move_in_execution(self.create_task_and_execute({
            'level': self.room.level,
            'building_id': self.room.building_id,
            'room_number': self.room.number,
        }))
        assert not self.user.hosts

    def test_successful_move_in_execution_minimal(self):
        self.assert_successful_move_in_execution(self.create_task_and_execute({
            'mac': self.mac,
            'level': self.room.level,
            'building_id': self.room.building_id,
            'room_number': self.room.number,
        }))
        assert len(self.user.hosts) == 1
        [host] = self.user.hosts
        assert len(host.interfaces) == 1
        [interface] = host.interfaces
        assert interface.mac == self.mac

    def assert_successful_move_in_execution(self, task: Task):
        assert task.status == TaskStatus.EXECUTED
        assert self.user.room == self.room

    def assert_failing_move_execution(self, task: Task, error_needle: str):
        assert task.status == TaskStatus.FAILED
        assert len(task.errors) == 1
        [error] = task.errors
        assert error_needle in error.lower()
        assert self.user.room is None

    def create_task_and_execute(self, params):
        return create_task_and_execute(TaskType.USER_MOVE_IN, self.user, params)
