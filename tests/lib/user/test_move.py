from datetime import timedelta

from pycroft.lib import user as UserHelper
from pycroft.model import session
from pycroft.model.task import Task, UserTask
from pycroft.model.task_serialization import UserMoveParams
from tests import FactoryDataTestBase, factories, UserFactory
from tests.factories import UserWithHostFactory


class Test_User_Move(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        # we just create the subnet to ensure it stays the same when in the same building
        subnet = factories.SubnetFactory()
        self.user = UserWithHostFactory(
            room__patched_with_subnet=True,
            room__patch_ports__switch_port__default_vlans__subnets=[subnet]
        )
        self.processing_user = UserFactory()
        self.old_room = self.user.room
        assert all(h.room == self.old_room for h in self.user.hosts)
        self.new_room_other_building = factories.RoomFactory(patched_with_subnet=True)
        self.new_room_same_building = factories.RoomFactory(
            building=self.old_room.building,
            patched_with_subnet=True,
            patch_ports__switch_port__default_vlans__subnets=[subnet],
        )

    def test_move_scheduling(self):
        when = session.utcnow() + timedelta(days=1)
        UserHelper.move(
            self.user,
            building_id=self.new_room_other_building.building.id,
            level=self.new_room_other_building.level,
            room_number=self.new_room_other_building.number,
            processor=self.processing_user,
            when=when,
        )
        tasks = self.session.query(Task).all()
        assert len(tasks) == 1
        [task] = tasks
        assert isinstance(task, UserTask)
        assert task.user == self.user
        assert task.parameters == UserMoveParams(
            building_id=self.new_room_other_building.building.id,
            level=self.new_room_other_building.level,
            room_number=self.new_room_other_building.number,
        )

    def test_0010_moves_into_same_room(self):
        self.assertRaises(
            AssertionError, UserHelper.move, self.user, self.old_room.building.id,
            self.old_room.level, self.old_room.number, self.processing_user)

    def test_0020_moves_into_other_building(self):
        UserHelper.move(
            self.user, self.new_room_other_building.building.id,
            self.new_room_other_building.level,
            self.new_room_other_building.number, self.processing_user,
        )
        self.assertEqual(self.user.room, self.new_room_other_building)
        self.assertEqual(self.user.hosts[0].room, self.new_room_other_building)
        # TODO test for changing ip
