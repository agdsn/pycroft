import pytest

from pycroft.model.task import TaskType
from tests.factories.task import TaskFactory, UserTaskFactory
from web import make_app
from web.blueprints.task import task_object


@pytest.fixture(scope='session')
def app():
    return make_app()


@pytest.mark.parametrize('task', [
    UserTaskFactory.build(
        type=TaskType.USER_MOVE,
        user__id=5,
        parameters_json={'building_id': 1, 'level': 3, 'room_number': 'Test'},
    )
])
def test_task_object_creation(app, task):
    object = task_object(task)
