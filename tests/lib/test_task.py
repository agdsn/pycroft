#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import datetime

import pytest

from pycroft.lib.task import cancel_task, manually_execute_task, reschedule_task
from pycroft.model.task import TaskType, TaskStatus
from pycroft.model.task_serialization import UserMoveParams
from tests.factories import UserFactory, UserTaskFactory, RoomFactory


class TestTaskExecution:
    @pytest.fixture(scope="class")
    def old_room(self, class_session):
        return RoomFactory()

    @pytest.fixture(scope="class")
    def new_room(self, class_session):
        return RoomFactory()

    @pytest.fixture(scope="class")
    def user(self, class_session, old_room):
        return UserFactory(room=old_room)

    # not `class` scoped because it changes its `Task.status`
    @pytest.fixture
    def task(self, class_session, user, new_room, processor):
        return UserTaskFactory(
            user=user, type=TaskType.USER_MOVE,
            created=datetime.datetime.now() - datetime.timedelta(days=1),
            due=datetime.datetime.now() + datetime.timedelta(days=7),
            parameters=UserMoveParams(room_number=new_room.number,
                                      level=new_room.level,
                                      building_id=new_room.building_id),
            creator=processor,
        )

    def test_task_defaults(self, task):
        assert task.status == TaskStatus.OPEN
        assert task.errors is None

    def test_task_cancel(self, task, processor, old_room, user):
        cancel_task(task, processor)

        assert user.room == old_room
        assert task.status == TaskStatus.CANCELLED
        assert task.latest_log_entry.author == processor

    def test_task_manually_execute(self, session, utcnow, task, processor, new_room, user):
        manually_execute_task(task, processor)
        now = utcnow

        assert user.room == new_room
        assert task.status == TaskStatus.EXECUTED
        assert task.due == now
        assert len(logs := task.log_entries) == 1
        assert logs[0].author == processor

    def test_task_reschedule(self, task, processor, old_room, user):
        new_due_date = datetime.datetime.now() + datetime.timedelta(days=5)
        reschedule_task(task, new_due_date, processor=processor)
        assert user.room == old_room
        assert task.status == TaskStatus.OPEN
        assert task.due == new_due_date
        assert task.latest_log_entry.author == processor

