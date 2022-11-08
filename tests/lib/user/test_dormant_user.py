import typing as t
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.interval import open
from pycroft.lib import user as UserHelper
from pycroft.model import session
from pycroft.model.address import Address
from pycroft.model.facilities import Room
from pycroft.model.task import Task, TaskType, TaskStatus
from pycroft.model.task_serialization import UserMoveOutParams
from pycroft.model.user import User
from tests.legacy_base import FactoryWithConfigDataTestBase
from tests.factories import RoomFactory, AddressFactory, UserFactory
from tests.lib.user.task_helpers import create_task_and_execute


class TestMovedInUser:
    @pytest.fixture(scope="class")
    def user(self, class_session, config):
        return UserFactory.create(
            with_host=True,
            with_membership=True,
            membership__group=config.member_group,
        )

    @pytest.fixture(scope="class")
    def other_room(self, class_session) -> Room:
        return RoomFactory.create()

    @pytest.fixture
    def move_out(
        self, session, processor, utcnow
    ) -> t.Callable[[User, str | None], None]:
        def move_out(user: User, comment: str | None = None) -> None:
            UserHelper.move_out(
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
        old_address = user.address

        move_out(user, "")
        assert user.active_memberships(when=open(utcnow, None)) == []
        assert user.room is None
        assert user.address == old_address

    def test_move_out_keeps_custom_address(self, user, customize_address, move_out):
        address = customize_address(user)
        move_out(user, "")
        assert user.address == address

    @pytest.fixture
    def move(self, session, processor) -> t.Callable[[User, Room], None]:
        def move(user, room):
            UserHelper.move(
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
