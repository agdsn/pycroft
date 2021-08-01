from datetime import datetime, timedelta

import pytest

from pycroft.model.task import TaskType, UserTask
from tests.factories.task import UserTaskFactory
from web.blueprints.task import task_row


@pytest.fixture(scope='function')
def task_request_ctx(app):
    """This provides us with a request context with a valid URL.

    Because flask recognizes this URL to belong to an endpoint in the `task` blueprint,
    this is needed for relative `url_for` calls in said blueprint to work.
    """
    ctx = app.test_request_context('/task/user/json')
    ctx.push()
    yield
    ctx.pop()


@pytest.mark.parametrize('task', [
    UserTaskFactory.build(
        type=TaskType.USER_MOVE,
        created=datetime.now() - timedelta(days=1),
        id=1,
        user__id=5,
        creator__id=7,
        parameters_json={'building_id': 1, 'level': 3, 'room_number': 'Test'},
    )
])
def test_task_object_creation(app, task: UserTask, session, task_request_ctx):
    object = task_row(task)
    assert object['user']['title'] is not None
    assert object['user']['href'] is not None
