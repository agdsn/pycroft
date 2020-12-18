import os

from datetime import timedelta
from typing import List

from celery import Celery
from celery.schedules import crontab
from sqlalchemy.orm import with_polymorphic

from pycroft.helpers.task import DBTask
from pycroft.lib.logging import log_task_event
from pycroft.lib.mail import send_mails, Mail, RetryableException, TaskFailedTemplate
from pycroft.lib.task import task_type_to_impl
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.swdd import swdd_vo, swdd_import, swdd_vv
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

        if task.status == TaskStatus.FAILED:
            from pycroft.lib.user import user_send_mail

            user_send_mail(task.creator, TaskFailedTemplate(), True)


@app.task(base=DBTask)
def remove_old_traffic_data():
    TrafficVolume.q.filter(
        TrafficVolume.timestamp < (session.utcnow() - timedelta(7))).delete()

    session.session.commit()

    print("Deleted old traffic data")


@app.task(base=DBTask)
def refresh_swdd_views():
    swdd_vo.refresh()
    swdd_vv.refresh()
    swdd_import.refresh()

    session.session.commit()

    print("Refreshed swdd views")


@app.task(ignore_result=True, rate_limit=1, bind=True)
def send_mails_async(self, mails: List[Mail]):
    success = False
    failures = len(mails)

    try:
        success, failures = send_mails(mails)
    except RetryableException:
        self.retry(countdown=1800, max_retries=96)
        print("Retrying mail task in 30min")
    except RuntimeError:
        pass

    if not success:
        print("Could not send all mails! ({}/{} failed)".format(failures, len(mails)))


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
        'refresh-swdd-views':{
            'task': 'pycroft.task.refresh_swdd_views',
            'schedule': timedelta(hours=3)
        }
    },
    CELERY_ENABLE_UTC=True,
    CELERY_TIMEZONE='Europe/Berlin')
