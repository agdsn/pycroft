Celery
======

Manual task execution
---------------------

Start a shell
    ``docker compose run --rm dev-app shell``

Activate the virtual environment
    ``. ~/venv/bin/activate``

Run a ``celery`` command
    ``celery -A pycroft.task call pycroft.task.execute_scheduled_tasks``

If any issues come up, ensure that the ``dummy-worker`` is not started
and restart the actual celery worker.

