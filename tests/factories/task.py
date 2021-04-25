import datetime

import factory

from pycroft.model.task import UserTask, TaskType, Task, TaskStatus
from tests.factories.base import BaseFactory


def yesterday():
    return datetime.datetime.today() - datetime.timedelta(days=1)


class TaskFactory(BaseFactory):
    class Meta:
        model = Task

    type: TaskType = None
    due = None
    parameters_json = None
    created = None
    creator = factory.SubFactory('tests.factories.UserFactory')
    status: TaskStatus = TaskStatus.OPEN
    errors = None

    class Params:
        due_yesterday = factory.Trait(
            due=factory.LazyFunction(yesterday),
            created=factory.LazyFunction(yesterday),
        )


class UserTaskFactory(TaskFactory):
    class Meta:
        model = UserTask

    user = factory.SubFactory('tests.factories.Userfactory')
