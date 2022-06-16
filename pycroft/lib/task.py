import logging
import typing
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Mapping, TypeVar, Generic

from marshmallow import ValidationError
from sqlalchemy.orm import with_polymorphic

from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.logging import log_task_event
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.task import UserTask, Task, TaskType, TaskStatus
from pycroft.model.task_serialization import UserMoveOutParams, UserMoveParams, UserMoveInParams, \
    TaskParams
from pycroft.model.user import User

TParams = TypeVar('TParams', bound=TaskParams)
TTask = TypeVar('TTask', bound=Task)

logger = logging.getLogger('pycroft.task')


# the generic parameters don't actually matter because
# to determine the type parameter at construction we would need
# dependent types, so we're always just instantiating
# `TaskImpl = TaskImpl[Any, Any]`, anyway.
class TaskImpl(ABC, Generic[TTask, TParams]):
    @property
    @abstractmethod
    def name(self):
        ...

    @property
    @abstractmethod
    def type(self):
        ...

    new_status = None
    errors: list[str] = list()

    @abstractmethod
    @with_transaction
    def schedule(self, *args, **kwargs):
        ...

    @with_transaction
    def execute(self, task: TTask):
        self.new_status = TaskStatus.FAILED
        self.errors = list()

        try:
            parameters: TParams = typing.cast(TParams, task.parameters)
        except ValidationError as e:
            self.errors.append(f"Failed to parse parameters: {e.messages}")
            logger.error('Failed to deserialize parameters', exc_info=True)
        else:
            self._execute(task, parameters)

    @abstractmethod
    def _execute(self, task: TTask, parameters: TParams):
        ...


class UserTaskImpl(TaskImpl, ABC):
    def schedule(self, due, user, parameters, processor):
        if due < session.utcnow():
            raise ValueError("the due date must be in the future")

        task = UserTask(type=self.type,
                        due=due,
                        creator=processor,
                        created=session.utcnow(),
                        user=user)

        task.parameters = parameters

        return task


class UserMoveOutTaskImpl(UserTaskImpl):
    name = "Auszug"
    type = TaskType.USER_MOVE_OUT

    def _execute(self, task: UserTask, parameters: UserMoveOutParams):
        from pycroft.lib import user as lib_user
        if task.user.room is None:
            self.errors.append("Tried to move out user, but user was not living in a dormitory")
            return

        lib_user.move_out(user=task.user,
                          comment=parameters.comment,
                          processor=task.creator,
                          when=session.utcnow(),
                          end_membership=parameters.end_membership)

        self.new_status = TaskStatus.EXECUTED


class UserMoveTaskImpl(UserTaskImpl):
    name = "Umzug"
    type = TaskType.USER_MOVE

    def _execute(self, task, parameters: UserMoveParams):
        from pycroft.lib import user as lib_user
        if task.user.room is None:
            self.errors.append("Tried to move in user, "
                               "but user was already living in a dormitory.")
            return

        room = lib_user.get_room(
            room_number=parameters.room_number,
            level=parameters.level,
            building_id=parameters.building_id,
        )

        if room is None:
            self.errors.append("Tried to move user, but target room did not exist.")
            return

        lib_user.move(
            user=task.user,
            building_id=room.building.id,
            level=room.level,
            room_number=room.number,
            comment=parameters.comment,
            processor=task.creator,
        )

        self.new_status = TaskStatus.EXECUTED


class UserMoveInTaskImpl(UserTaskImpl):
    name = "Einzug"
    type = TaskType.USER_MOVE_IN

    def _execute(self, task, parameters: UserMoveInParams):
        from pycroft.lib import user as lib_user

        if task.user.room is not None:
            self.errors.append("Tried to move in user, "
                               "but user was already living in a dormitory.")
            return

        room = lib_user.get_room(
            room_number=parameters.room_number,
            level=parameters.level,
            building_id=parameters.building_id,
        )

        if room is None:
            self.errors.append(
                "Tried to move in user, but target room did not exist.")
            return

        lib_user.move_in(user=task.user,
                         building_id=room.building.id,
                         level=room.level,
                         room_number=room.number,
                         mac=parameters.mac,
                         processor=task.creator,
                         birthdate=parameters.birthdate,
                         host_annex=parameters.host_annex,
                         begin_membership=parameters.begin_membership,
                         )

        self.new_status = TaskStatus.EXECUTED


task_type_to_impl: Mapping[TaskType, type[UserTaskImpl]] = {
    TaskType.USER_MOVE: UserMoveTaskImpl,
    TaskType.USER_MOVE_IN: UserMoveInTaskImpl,
    TaskType.USER_MOVE_OUT: UserMoveOutTaskImpl
}


def get_task_implementation(task: Task) -> TaskImpl:
    return task_type_to_impl.get(task.type)()


@with_transaction
def schedule_user_task(task_type, due, user, parameters: TaskParams, processor):
    if due < session.utcnow():
        raise ValueError("the due date must be in the future")

    task = UserTask(type=task_type,
                    due=due,
                    creator=processor,
                    created=session.utcnow(),
                    user=user)

    task.parameters = parameters
    session.session.add(task)

    return task


def get_active_tasks_by_type(type):
    task_and_subtypes = with_polymorphic(Task, "*")
    return session.session.query(
        task_and_subtypes.where(task_and_subtypes.type == type)
    ).all()


@with_transaction
def cancel_task(task: Task, processor: User):
    if task.status != TaskStatus.OPEN:
        raise ValueError("Cannot cancel a task that is not open")

    message = deferred_gettext("Cancelled task {}.").format(task.id)
    log_task_event(message, processor, task)
    task.status = TaskStatus.CANCELLED


def manually_execute_task(task: Task, processor: User):
    if task.status != TaskStatus.OPEN:
        raise ValueError("Cannot execute a task that is not open")

    get_task_implementation(task).execute(task)

    task.due = session.utcnow()
    log_task_event(deferred_gettext("Manually executed task {}").format(task.id).to_json(),
                   author=processor, task=task)
    task.status = TaskStatus.EXECUTED


def reschedule_task(task: Task, due: datetime, processor: User):
    if task.status != TaskStatus.OPEN:
        raise ValueError("Cannot execute a task that is not open")

    task.due = due
    log_task_event(deferred_gettext("Rescheduled task {task_id} to {new_due}")
                   .format(task_id=task.id, new_due=due).to_json(),
                   author=processor, task=task)
