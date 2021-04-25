from datetime import datetime, timedelta

from pycroft.lib import user as UserHelper
from pycroft.model import session
from pycroft.model.task import Task
from pycroft.model.task_serialization import UserMoveInParams
from tests import FactoryDataTestBase, factories, UserFactory
from . import ExampleUserData


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
            self.assertIn(group, active_user_groups)

        self.assertFalse(self.user.has_property("reduced_membership_fee"))

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
