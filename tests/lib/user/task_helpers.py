from pycroft.model.session import session
from pycroft.model.task import Task, TaskType
from pycroft.model.user import User
from pycroft.task import execute_scheduled_tasks
from tests.factories.task import UserTaskFactory


def create_task_and_execute(task_type: TaskType, user: User, params) -> Task:
    task = UserTaskFactory(
        type=task_type, user=user, parameters_json=params, due_yesterday=True,
    )
    with session.begin_nested():
        session.add(task)

    assert Task.q.all()
    execute_scheduled_tasks()
    return task
