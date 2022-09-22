"""
pycroft.task
~~~~~~~~~~~~

This module defines celery tasks to run tasks
(as persisted in the database by means of `pycroft.model.task`)
by using implementations as defined in `pycroft.lib.task`
(see :class:`TaskImpl <pycroft.lib.task.TaskImpl>`).
"""
import logging
import os
import sys
import typing as t
from datetime import timedelta

import sentry_sdk
from celery import Celery, Task as CeleryTask
from celery.schedules import crontab
from celery.utils.log import get_task_logger
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sqlalchemy.orm import with_polymorphic, Session, scoped_session, sessionmaker
from sqlalchemy.orm.exc import ObjectDeletedError

from pycroft.lib.finance import get_negative_members
from pycroft.lib.logging import log_task_event
from pycroft.lib.mail import send_mails, Mail, RetryableException, \
    TaskFailedTemplate, \
    MemberNegativeBalance, send_template_mails
from pycroft.lib.task import get_task_implementation
from pycroft.model import session
from pycroft.model.finance import BankAccountActivity
from pycroft.model.session import with_transaction, session, set_scoped_session
from pycroft.model.swdd import swdd_vo, swdd_import, swdd_vv
from pycroft.model.task import Task, TaskStatus
from pycroft.model.traffic import TrafficVolume
from scripts.connection import try_create_connection

if dsn := os.getenv('PYCROFT_SENTRY_DSN'):
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # INFO / WARN create breadcrumbs, just as SQL queries
        event_level=logging.ERROR,  # errors and above create breadcrumbs
    )

    sentry_sdk.init(
        dsn=dsn,
        integrations=[CeleryIntegration(), logging_integration],
        traces_sample_rate=1.0,
    )

app = Celery('tasks', backend=os.getenv('PYCROFT_CELERY_RESULT_BACKEND_URI'),
             broker=os.getenv('PYCROFT_CELERY_BROKER_URI'))

logger = get_task_logger(__name__)


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


class DBTask(CeleryTask):
    """
    Base class for tasks which use the database.
    """

    connection = None
    engine = None

    def run(self, *args: t.Any, **kwargs: t.Any) -> None:
        pass

    def after_return(
        self,
        status: str,
        retval: t.Any,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: t.Any = None,
    ) -> None:
        session.close()

    def __init__(self) -> None:
        in_celery = sys.argv and sys.argv[0].endswith("celery") and "worker" in sys.argv
        if not in_celery:
            return
        try:
            connection_string = os.environ["PYCROFT_DB_URI"]
        except KeyError:
            raise RuntimeError(
                "Environment variable PYCROFT_DB_URI must be "
                "set to an SQLAlchemy connection string."
            )

        self.connection, self.engine = try_create_connection(
            connection_string, 5, logger=logging.getLogger("tasks"), echo=False
        )

        set_scoped_session(
            t.cast(Session, scoped_session(sessionmaker(bind=self.engine)))
        )

    def __del__(self) -> None:
        if self.connection is not None:
            self.connection.close()


@app.task(base=DBTask)
def execute_scheduled_tasks():
    """For all tasks which are due, call their respective implementation and handle the result.

    Implementations are given by `task_type_to_impl`.
    Errors are reported to the creator via `send_user_send_mail`.
    """
    task_and_subtypes = with_polymorphic(Task, "*")
    tasks = (session.session.query(task_and_subtypes)
             .filter(task_and_subtypes.status == TaskStatus.OPEN,
                     task_and_subtypes.due <= session.utcnow())
             .all())

    print(f"executing {len(tasks)} scheduled tasks")

    for task in tasks:
        repair_session()

        task_impl = get_task_implementation(task)

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
                print(f"Error while executing task: {error}")

        try:
            write_task_message(
                task,
                f"Processed {task.type.name} task. Status: {task.status.name}",
                log=True
            )
        except ObjectDeletedError:
            logger.error("Task instance deleted (broken polymorphism?)", exc_info=True)
            continue

        session.session.commit()

        if task.status == TaskStatus.FAILED:
            send_template_mails(['support@agdsn.de'], TaskFailedTemplate(), task=task)


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


@app.task(base=DBTask)
def mail_negative_members():
    from pycroft.lib.user import user_send_mails

    activity = BankAccountActivity.q.order_by(BankAccountActivity.imported_at.desc()).first()
    if activity.imported_at.date() >= session.utcnow().date() - timedelta(days=2):
        negative_users = get_negative_members()
        user_send_mails(negative_users, MemberNegativeBalance())
    else:
        mail = Mail("Finanzen",
                    "finanzen@lists.agdsn.de",
                    "Automatische Zahlungsrückstands-Mail fehlgeschlagen",
                    body_plain="Der Import ist nicht aktuell genug.")
        send_mails_async.delay([mail])


@app.task(ignore_result=True, rate_limit=1, bind=True)
def send_mails_async(self, mails: list[Mail]):
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
        print(f"Could not send all mails! ({failures}/{len(mails)} failed)")


app.conf.update(
    beat_schedule={
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
        },
        'mail-negative-members': {
            'task': 'pycroft.task.mail_negative_members',
            'schedule': crontab(0, 0, day_of_month=5)
        }
    },
    enable_utc=True,
    timezone='Europe/Berlin',
    accept_content={'pickle'},
    task_serializer='pickle',
    result_serializer='pickle',
    broker_transport_options={
        "client_properties": {"connection_name": "pycroft celery worker"},
    },
)
