"""
hades_logs
----------

This module provides access to Hades' radius logs utilizing its celery
RPC api.
"""

from celery import Celery, signature
from celery.exceptions import TimeoutError as CeleryTimeoutError
from kombu.exceptions import OperationalError
from flask.globals import current_app
from werkzeug import LocalProxy


__all__ = [
    'HadesTimeout',
    'HadesLogs',
    'hades_logs'
]


_CONFIGURATION_DOCS = """\
This Flask application utilizes the `HadesLogs` extension, \
which needs certain config variables.

A minimal example configuration would look like this:
> app.config['HADES_CELERY_APP_NAME'] = 'hades'
> app.config['HADES_BROKER_URI'] = 'pyamqp://user:password@rabbitmq_host:5762/vhost'
> app.config['HADES_RESULT_BACKEND_URI'] = 'pyamqp://user:password@rabbitmq_host:5762/vhost'\
"""
class HadesError(Exception):
    pass


class HadesTimeout(TimeoutError, HadesError):
    pass


class HadesConfigError(RuntimeError, HadesError):
    pass


class HadesLogs:
    """The ``HadesLogs`` Flask extension

    This extension provides access to the Hades RPC.  The core
    functionality is provided by :py:meth:`fetch_logs`.

    You need to provide the following configuration to
    :py:obj:`app.config`:

        - 'HADES_CELERY_APP_NAME': The Name of the celery app

        - 'HADES_BROKER_URI': The broker URI

        - 'HADES_RESULT_BACKEND_URI': The URI of the Result backend

        - 'HADES_TIMEOUT' (Optional, default=5): The Timeout to wait
          with each task in seconds.

    Usage:

    >>> from flask import Flask

    >>> from hades_logs import HadesLogs

    >>> app = Flask('test')

    >>> logs = HadesLogs(app)

    >>> logs.fetch_logs(<nasip>, <portid>)
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        app.extensions['hades_logs'] = self

        try:
            app_name = app.config['HADES_CELERY_APP_NAME']
            broker_uri = app.config['HADES_BROKER_URI']
            backend_uri = app.config['HADES_RESULT_BACKEND_URI']
        except KeyError as e:
            raise KeyError("Missing config key: {}\n{}"
                           .format(e, _CONFIGURATION_DOCS)) from e
        self.timeout = app.config.get('HADES_TIMEOUT', 5)

        self.celery = Celery(app_name, broker=broker_uri, backend=backend_uri)

    def create_task(self, name, *args, **kwargs):
        """Create a Celery task object by name, args and kwargs

        ``*args`` and ``**kwargs`` are passed to the corresponding
        parameters of :py:func:`Celery.signature(name, args, kwargs)`

        :param name: The name of the task without the celery app name.
            Assembling is done using :py:attr:`self.celery.main`.

        :returns: the signature of the task

        :rtype: :py:obj:`celery.Signature`
        """
        full_task_name = '{}.{}'.format(self.celery.main, name)
        return self.celery.signature(full_task_name, args=args, kwargs=kwargs)

    def fetch_logs(self, nasipaddress, nasportid, limit=100):
        """Fetch the auth logs of the given port

        :param ipaddr nasipaddress: The IP address of the NAS
        :param str nasportid: The port identifier (e.g. `C12`) of the
            NAS port

        :returns: the result of the task (see
                  ``get_port_auth_attempts`` in hades)

        :raises HadesTimeout: on timeouts, e.g. when the task takes
            too long to be executed by a worker or when the broker is
            down.
        """
        task = self.create_task(name='get_port_auth_attempts',
                                nasipaddress=nasipaddress, nasportid=nasportid,
                                limit=limit)

        try:
            return task.apply_async().wait(timeout=self.timeout)
        except CeleryTimeoutError as e:
            raise HadesTimeout("The Hades lookup task has timed out") from e
        except OperationalError as e:
            # The `OperationalError` is thrown when e.g. the broker is
            # down
            if "timeout" in str(e).lower():
                raise HadesTimeout("The Hades lookup task has timed out") from e
            else:
                raise

from datetime import datetime
test_hades_logs = [
    ("Auth-Reject", "", "00:de:ad:be:ef:00", datetime(2017, 5, 20, 18, 25), None),
    ("Auth-Access", "Wu5_untagged", "00:de:ad:be:ef:00", datetime(2017, 4, 20, 18, 20), 15),
    ("Auth-Access", "unknown", "00:de:ad:be:ef:01", datetime(2017, 4, 20, 18, 5), 1001),
    ("Auth-Access", "traffic", "00:de:ad:be:ef:00", datetime(2017, 4, 20, 18, 0), 1001),
]

class DummyHadesLogs(HadesLogs):
    def init_app(self, app):
        app.extensions['hades_logs'] = self

    def create_task(self):
        raise NotImplementedError

    def fetch_logs(self, nasipaddress, nasportid, limit=100):
        return test_hades_logs


def _get_extension():
    try:
        return current_app.extensions['hades_logs']
    except KeyError:
        raise HadesConfigError("No HadesLogs instance registered to current Flask app")

hades_logs = LocalProxy(_get_extension)
