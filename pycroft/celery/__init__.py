# -*- coding: utf-8 -*-
from pycroft.model import session
from pycroft.model.celery_tasks import TestTask
from pycroft.model.session import with_transaction
from celery import Celery

__author__ = 'Florian Österreich'


celery_app = Celery('tasks', broker='amqp://guest@localhost//')


#@with_transaction
def test_task(text, execution_date):
    new_test_task = TestTask(text=text)
    session.session.add(new_test_task)
    session.session.commit()
    _test_task.apply_async(kwargs={'task_id': new_test_task.id}, eta=execution_date)


@celery_app.task
def _test_task(task_id):
    task = TestTask.q.get(task_id)
    print task.text
