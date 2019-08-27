import os

from datetime import timedelta

from celery import Celery
from sqlalchemy.orm import with_polymorphic

from pycroft.helpers.task import DBTask
from pycroft.lib.logging import log_task_event
from pycroft.lib.task import task_type_to_impl
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.task import Task, TaskStatus
from pycroft.model.traffic import TrafficVolume

app = Celery('tasks', backend=os.environ['PYCROFT_CELERY_RESULT_BACKEND_URI'],
             broker=os.environ['PYCROFT_CELERY_BROKER_URI'])


@with_transaction
def write_task_message(task, message, log=False):
    message = str(message)

    if log:
        log_task_event(message, task.creator, task)

    print(message)


def repair_session():
    if not session.session.is_active:
        session.session.rollback()
        print("Repaired session (rollback).")


@app.task(base=DBTask)
def execute_scheduled_tasks():
    tasks = (session.session.query(with_polymorphic(Task, "*"))
             .filter(Task.status == TaskStatus.OPEN,
                     Task.due <= session.utcnow())
             .all())

    print("executing {} scheduled tasks".format(len(tasks)))

    for task in tasks:
        repair_session()

        task_impl = task_type_to_impl.get(task.type)()

        try:
            task_impl.execute(task)
        except Exception as e:
            task_impl.errors.append(str(e))

        repair_session()

        if task_impl.new_status is not None:
            task.status = task_impl.new_status

        if task_impl.errors:
            task.errors = task_impl.errors

            for error in task.errors:
                print("Error while executing task: {}".format(error))

        write_task_message(task, "Processed {} task. Status: {}".format(
            task.type.name, task.status.name), log=True)

        session.session.commit()


@app.task(base=DBTask)
def remove_old_traffic_data():
    TrafficVolume.q.filter(
        TrafficVolume.timestamp < (session.utcnow() - timedelta(7))).delete()

    session.session.commit()

    print("Deleted old traffic data")


app.conf.update(
    CELERYBEAT_SCHEDULE={
        'execute-scheduled-tasks': {
            'task': 'pycroft.task.execute_scheduled_tasks',
            'schedule': timedelta(hours=1)
        },
        'remove-old-traffic-data': {
            'task': 'pycroft.task.remove_old_traffic_data',
            'schedule': timedelta(days=1)
        },
    },
    CELERY_TIMEZONE='UTC')
