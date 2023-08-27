"""
hades_logs
----------

This module provides access to Hades' radius logs utilizing its celery
RPC api.
"""
import typing as t
import logging

from celery.exceptions import TimeoutError as CeleryTimeoutError
from flask.globals import current_app
from kombu.exceptions import OperationalError
from werkzeug.local import LocalProxy

from .app import HadesCelery
from .exc import HadesConfigError, HadesOperationalError, HadesTimeout
from .parsing import RadiusLogEntry, reduce_radius_logs


_CONFIGURATION_DOCS = """\
This Flask application utilizes the `HadesLogs` extension, \
which needs certain config variables.

A minimal example configuration would look like this:
> app.config['HADES_CELERY_APP_NAME'] = 'hades'
> app.config['HADES_BROKER_URI'] = 'amqp://user:password@rabbitmq_host:5672/vhost'
> app.config['HADES_RESULT_BACKEND_URI'] = 'rpc://user:password@rabbitmq_host:5672/vhost'\
"""


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

        - 'HADES_ROUTING_KEY' (Optional, default=None): The routing
          key to use for the celery messages

    Usage:

    >>> from flask import Flask

    >>> from hades_logs import HadesLogs

    >>> app = Flask('test')

    >>> logs = HadesLogs(app)

    >>> logs.fetch_logs(<nasip>, <portid>)
    """
    def __init__(self, app=None):
        self.app = app
        self.logger = logging.getLogger('hades_logs')
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        try:
            app_name = app.config['HADES_CELERY_APP_NAME']
            broker_uri = app.config['HADES_BROKER_URI']
            backend_uri = app.config['HADES_RESULT_BACKEND_URI']
            routing_key = app.config.get('HADES_ROUTING_KEY', 'masters.root.agdsn')
        except KeyError as e:
            self.logger.warning("Missing config key: %s\n%s", e, _CONFIGURATION_DOCS)
            raise KeyError(f"Missing config key: {e}") from e
        self.timeout = app.config.get('HADES_TIMEOUT', 5)
        task_default_exchange = app.config.get(
            "HADES_TASK_DEFAULT_EXCHANGE", "hades.rpc-call"
        )
        result_exchange = app.config.get("HADES_RESULT_EXCHANGE", "hades.rpc-result")

        self.celery = HadesCelery(
            app_name,
            broker=broker_uri,
            backend=backend_uri,
            task_default_exchange=task_default_exchange,
            result_exchange=result_exchange,
            routing_key=routing_key,
        )
        # Gets run only on success
        self.logger.info("Initialization complete, registering 'hades_logs' extension")
        app.extensions['hades_logs'] = self

    def create_task(self, name, *args, **kwargs):
        """Create a Celery task object by name, args and kwargs

        ``*args`` and ``**kwargs`` are passed to the corresponding
        parameters of :py:func:`Celery.signature(name, args, kwargs)`

        :param name: The name of the task without the celery app name.
            Assembling is done using :py:attr:`self.celery.main`.

        :returns: the signature of the task

        :rtype: :py:obj:`celery.Signature`
        """
        full_task_name = f'{self.celery.main}.{name}'
        return self.celery.signature(full_task_name, args=args, kwargs=kwargs)

    def fetch_logs(
        self, nasipaddress: str, nasportid: str, limit: int = 100, reduced: bool = True
    ) -> t.Iterator[RadiusLogEntry]:
        """Fetch the auth logs of the given port

        :param ipaddr nasipaddress: The IP address of the NAS
        :param str nasportid: The port identifier (e.g. `C12`) of the
            NAS port

        :returns: the result of the task (see
                  ``get_port_auth_attempts`` in hades)
        :rtype: iterable (generator if :param:`reduced`)

        :raises HadesTimeout: raised when no response arrives in the time window
            configured by the `timeout` parameter.
        """
        if reduced:
            reductor = reduce_radius_logs
        else:
            def reductor(x):
                return x

        task = self.create_task(name='get_auth_attempts_at_port',
                                nas_ip_address=nasipaddress, nas_port_id=nasportid,
                                limit=limit)

        return reductor(RadiusLogEntry(*e) for e in self.wait_for_task(task))

    def wait_for_task(self, task):
        self.logger.info("Waiting for task: %s", task)
        try:
            return task.apply_async().wait(timeout=self.timeout)
        except CeleryTimeoutError as e:
            raise HadesTimeout("The Hades lookup task has timed out") from e
        except OSError as e:
            if "timeout" in str(e).lower():
                # TODO this is mainly to make this error visible once it occurs (sentry).
                # Since timeouts should actually be handled by the branch above,
                # I'm not quite sure in what cases an `OSError` would be thrown!
                self.logger.error("Hades task timed out with OSError", exc_info=True)
                raise HadesTimeout("The Hades lookup task has timed out (from OSError)") from e
            else:
                raise
        except OperationalError as e:
            raise HadesOperationalError("OSError when fetching hades logs") from e


def _get_extension():
    try:
        return current_app.extensions['hades_logs']
    except KeyError:
        raise HadesConfigError(
            "No HadesLogs instance registered to current Flask app"
        ) from None


hades_logs: HadesLogs = LocalProxy(_get_extension)
