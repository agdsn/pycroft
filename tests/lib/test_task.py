#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import datetime

from pycroft.lib.task import cancel_task, manually_execute_task, reschedule_task
from pycroft.model import session
from pycroft.model.task import TaskType, TaskStatus
from pycroft.model.task_serialization import UserMoveParams
from tests.legacy_base import FactoryDataTestBase
from tests.factories import UserFactory, UserTaskFactory, RoomFactory


class TestTaskExecution(FactoryDataTestBase):
    def create_factories(self):
        self.admin = UserFactory()
        self.old_room = RoomFactory()
        self.new_room = RoomFactory()
        self.user = UserFactory(room=self.old_room)
        self.task = UserTaskFactory(
            user=self.user, type=TaskType.USER_MOVE,
            created=datetime.datetime.now() - datetime.timedelta(days=1),
            due=datetime.datetime.now() + datetime.timedelta(days=7),
            parameters=UserMoveParams(room_number=self.new_room.number,
                                      level=self.new_room.level,
                                      building_id=self.new_room.building_id),
            creator=self.admin,
        )

    def test_task_defaults(self):
        assert self.task.status == TaskStatus.OPEN
        assert self.task.errors is None

    def test_task_cancel(self):
        cancel_task(self.task, self.admin)
        self.session.commit()

        assert self.user.room == self.old_room
        assert self.task.status == TaskStatus.CANCELLED
        assert self.task.latest_log_entry.author == self.admin

    def test_task_manually_execute(self):
        manually_execute_task(self.task, self.admin)
        now = session.utcnow()
        self.session.commit()

        assert self.user.room == self.new_room
        assert self.task.status == TaskStatus.EXECUTED
        assert self.task.due == now
        assert len(logs := self.task.log_entries) == 1
        assert logs[0].author == self.admin

    def test_task_reschedule(self):
        new_due_date = datetime.datetime.now() + datetime.timedelta(days=5)
        reschedule_task(self.task, new_due_date,
                        processor=self.admin)
        assert self.user.room == self.old_room
        assert self.task.status == TaskStatus.OPEN
        assert self.task.due == new_due_date
        assert self.task.latest_log_entry.author == self.admin

