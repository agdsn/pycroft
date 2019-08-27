from abc import ABC, abstractmethod

from sqlalchemy.orm import with_polymorphic

from pycroft.lib.logging import log_task_event
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.session import with_transaction
from pycroft.model.task import UserTask, Task, TaskType, TaskStatus, \
    UserMoveSchema, UserMoveOutSchema, UserMoveInSchema


class TaskImpl(ABC):
    @property
    @abstractmethod
    def name(self):
        ...

    @property
    @abstractmethod
    def type(self):
        ...

    @property
    @abstractmethod
    def schema(self):
        ...

    new_status = None
    errors = list()

    @abstractmethod
    @with_transaction
    def schedule(self, *args, **kwargs):
        ...

    @with_transaction
    def execute(self, task):
        self.new_status = TaskStatus.FAILED
        self.errors = list()

        parameters, parse_errors = task.parameters

        if parse_errors:
            self.errors.append(
                "Failed to parse parameters: {}".format(parse_errors))
        else:
            self._execute(task, parameters)

    @abstractmethod
    def _execute(self, *args, **kwargs):
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
    schema = UserMoveOutSchema

    def _execute(self, task, parameters):
        from pycroft.lib import user as lib_user

        if task.user.room is not None:
            lib_user.move_out(user=task.user,
                              comment=parameters['comment'],
                              processor=task.creator,
                              when=session.utcnow(),
                              end_membership=parameters['end_membership'])

            self.new_status = TaskStatus.EXECUTED
        else:
            self.errors.append(
                "Tried to move out user, but user was not living in a dormitory")


class UserMoveTaskImpl(UserTaskImpl):
    name = "Umzug"
    type = TaskType.USER_MOVE
    schema = UserMoveSchema

    def _execute(self, task, parameters):
        from pycroft.lib import user as lib_user

        if task.user.room is not None:
            room = Room.q.filter_by(
                number=parameters['room_number'],
                level=parameters['level'],
                building_id=parameters['building_id']
            ).first()

            if room is not None:
                lib_user.move(task.user,
                              room.building.id,
                              room.level,
                              room.number,
                              task.creator)

                self.new_status = TaskStatus.EXECUTED
            else:
                self.errors.append(
                    "Tried to move user, but target room did not exist.")
        else:
            self.errors.append(
                "Tried to move in user, but user was already living in a dormitory.")


class UserMoveInTaskImpl(UserTaskImpl):
    name = "Einzug"
    type = TaskType.USER_MOVE_IN
    schema = UserMoveInSchema

    def _execute(self, task, parameters):
        from pycroft.lib import user as lib_user

        if task.user.room is None:
            room = Room.q.filter_by(
                number=parameters['room_number'],
                level=parameters['level'],
                building_id=parameters['building_id']
            ).first()

            if room is not None:
                lib_user.move_in(user=task.user,
                                 building_id=room.building.id,
                                 level=room.level,
                                 room_number=room.number,
                                 mac=parameters['mac'],
                                 processor=task.creator,
                                 birthdate=parameters['birthdate'],
                                 host_annex=parameters['host_annex'],
                                 begin_membership=parameters[
                                     'begin_membership']
                                 )

                self.new_status = TaskStatus.EXECUTED
            else:
                self.errors.append(
                    "Tried to move in user, but target room did not exist.")
        else:
            self.errors.append(
                "Tried to move in user, but user was already living in a dormitory.")


task_type_to_impl = {
    TaskType.USER_MOVE: UserMoveTaskImpl,
    TaskType.USER_MOVE_IN: UserMoveInTaskImpl,
    TaskType.USER_MOVE_OUT: UserMoveOutTaskImpl
}


@with_transaction
def schedule_user_task(task_type, due, user, parameters, processor):
    if due < session.utcnow():
        raise ValueError("the due date must be in the future")

    task = UserTask(type=task_type,
                    due=due,
                    creator=processor,
                    created=session.utcnow(),
                    user=user)

    task.parameters = parameters

    return task


def get_active_tasks_by_type(type):
    return session.session.query(
        with_polymorphic(Task, "*")
            .where(Task.type == type)
    ).all()


@with_transaction
def cancel_task(task, processor):
    if task.status != TaskStatus.OPEN:
        raise ValueError("Cannot cancel a task that is not open")

    log_task_event("Cancelled task {}.".format(task.id), processor, task)

    task.status = TaskStatus.CANCELLED
