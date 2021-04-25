from datetime import datetime, timezone, timedelta

from pycroft.helpers.interval import single
from pycroft.lib import user as UserHelper
from pycroft.model import session
from pycroft.model.task import Task, TaskType
from pycroft.model.task_serialization import UserMoveOutParams
from tests import FactoryWithConfigDataTestBase, UserFactory, MembershipFactory
from tests.factories import UserWithHostFactory, RoomFactory, AddressFactory


class MovedInUserTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        # We want a user who lives somewhere with a membership!
        super().create_factories()
        self.processor = UserFactory.create()
        self.user = UserWithHostFactory.create()
        self.membership = MembershipFactory.create(user=self.user,
                                                   group=self.config.member_group)
        self.other_room = RoomFactory.create()

    def move_out(self, user, comment=None):
        UserHelper.move_out(user, comment=comment or "", processor=self.processor,
                            when=session.utcnow())
        session.session.refresh(user)

    def customize_address(self, user):
        self.user.address = address = AddressFactory.create(city="Bielefeld")
        session.session.add(user)
        session.session.commit()
        self.assertTrue(user.has_custom_address)
        return address

    def test_move_out_keeps_address(self):
        self.assertFalse(self.user.has_custom_address)
        old_address = self.user.address

        self.move_out(self.user)
        self.assertEqual(
            self.user.active_memberships(when=single(datetime.now(timezone.utc))),
            []
        )
        self.assertIsNone(self.user.room)
        self.assertEqual(self.user.address, old_address)

    def test_move_out_keeps_custom_address(self):
        address = self.customize_address(self.user)
        self.move_out(self.user)
        self.assertEqual(self.user.address, address)

    def move(self, user, room):
        UserHelper.move(user, processor=self.processor,
                        building_id=room.building_id, level=room.level, room_number=room.number)
        session.session.refresh(user)

    def test_move_changes_address(self):
        self.move(self.user, self.other_room)
        self.assertEqual(self.user.address, self.other_room.address)

    def test_move_keeps_custom_address(self):
        address = self.customize_address(self.user)
        self.move(self.user, self.other_room)
        self.assertEqual(self.user.address, address)


class MoveOutSchedulingTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        # We want a user who lives somewhere with a membership!
        super().create_factories()
        self.processor = UserFactory.create()
        self.user = UserWithHostFactory.create(
            with_membership=True,
            membership__group=self.config.member_group,
        )

    def test_move_out_gets_scheduled(self, end_membership=None):
        for end_membership in (True, False):
            with self.subTest(end_membership=end_membership):
                old_room = self.user.room
                UserHelper.move_out(self.user, comment="", processor=self.processor,
                                    when=session.utcnow() + timedelta(days=1),
                                    end_membership=end_membership)
                assert self.user.room == old_room
                tasks = self.session.query(Task).all()
                assert len(tasks) == 1
                [task] = tasks
                assert task.type == TaskType.USER_MOVE_OUT
                assert task.parameters == UserMoveOutParams(comment="", end_membership=end_membership)
                session.session.delete(task)
