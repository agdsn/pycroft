from datetime import datetime, timezone, timedelta

from pycroft.helpers.interval import single, open
from pycroft.lib import user as UserHelper
from pycroft.model import session
from pycroft.model.task import Task, TaskType, TaskStatus
from pycroft.model.task_serialization import UserMoveOutParams
from tests.legacy_base import FactoryWithConfigDataTestBase
from tests.factories import RoomFactory, AddressFactory, UserFactory, \
    MembershipFactory
from tests.lib.user.task_helpers import create_task_and_execute


class MovedInUserTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        # We want a user who lives somewhere with a membership!
        super().create_factories()
        self.processor = UserFactory.create()
        self.user = UserFactory.create(with_host=True)
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
        assert user.has_custom_address
        return address

    def test_move_out_keeps_address(self):
        assert not self.user.has_custom_address
        old_address = self.user.address

        self.move_out(self.user)
        assert self.user.active_memberships(when=single(datetime.now(timezone.utc))) == []
        assert self.user.room is None
        assert self.user.address == old_address

    def test_move_out_keeps_custom_address(self):
        address = self.customize_address(self.user)
        self.move_out(self.user)
        assert self.user.address == address

    def move(self, user, room):
        UserHelper.move(user, processor=self.processor,
                        building_id=room.building_id, level=room.level, room_number=room.number)
        session.session.refresh(user)

    def test_move_changes_address(self):
        self.move(self.user, self.other_room)
        assert self.user.address == self.other_room.address

    def test_move_keeps_custom_address(self):
        address = self.customize_address(self.user)
        self.move(self.user, self.other_room)
        assert self.user.address == address


class MoveOutSchedulingTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        # We want a user who lives somewhere with a membership!
        super().create_factories()
        self.processor = UserFactory.create()
        self.user = UserFactory.create(
            with_membership=True,
            membership__group=self.config.member_group,
            with_host=True,
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


class MoveOutImplTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        # We want a user who lives somewhere with a membership!
        super().create_factories()
        self.user = UserFactory.create(
            with_membership=True,
            membership__group=self.config.member_group,
            with_host=True
        )

    def test_move_out_implementation(self):
        self.assert_successful_move_out_execution(self.create_task_and_execute(
            {"comment": "Dieser Kommentarbereich nun Eigentum der Bundesrepublik Deutschlands.",
             "end_membership": True}
        ))

    def test_move_out_impl_with_empty_comment(self):
        self.assert_successful_move_out_execution(
            self.create_task_and_execute({"comment": "", "end_membership": True})
        )

    def test_move_out_without_end_membership_fails(self):
        self.assert_failing_move_out_execution(
            self.create_task_and_execute({"comment": ""}),
            error_needle='end_membership',
        )

    def test_move_out_impl_without_comment_fails(self):
        self.assert_failing_move_out_execution(
            self.create_task_and_execute({"end_membership": True}),
            error_needle='comment',
        )

    def assert_successful_move_out_execution(self, task: Task):
        assert task.status == TaskStatus.EXECUTED
        assert self.user.room is None

        relevant_interval = open(datetime.now(timezone.utc) + timedelta(minutes=1), None)
        assert self.user.active_memberships(when=relevant_interval) == []

    def assert_failing_move_out_execution(self, task: Task, error_needle: str):
        assert task.status == TaskStatus.FAILED
        assert len(task.errors) == 1
        [error] = task.errors
        assert error_needle in error.lower()
        assert self.user.room is not None

    def create_task_and_execute(self, params):
        return create_task_and_execute(TaskType.USER_MOVE_OUT, self.user, params)
