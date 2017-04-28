from celery import Celery, signature
from celery.exceptions import TimeoutError
from flask.globals import current_app
from werkzeug import LocalProxy


_CONFIGURATION_DOCS = """\
This Flask application utilizes the `HadesLogs` extension, \
which needs certain config variables.

A minimal example configuration would look like this:
> app.config['HADES_CELERY_APP_NAME'] = 'hades'
> app.config['HADES_BROKER_URI'] = 'pyamqp://user:password@rabbitmq_host:5762/vhost'
> app.config['HADES_RESULT_BACKEND_URI'] = 'pyamqp://user:password@rabbitmq_host:5762/vhost'\
"""


class HadesTimeout(RuntimeError):
    pass


class HadesLogs:
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

        self.celery = Celery(app_name=app_name,
                             broker=broker_uri, backend=backend_uri)

    def create_task(self, name, *args, **kwargs):
        full_task_name = '{}.{}'.format(self.celery.main, name)
        return self.celery.signature(full_task_name, args=args, kwargs=kwargs)

    def fetch_logs(self, nasipaddress, nasportid):
        task = self.create_task(name='', nasipaddress=nasipaddress, nasportid=nasportid)

        try:
            task.apply_async().wait(timeout=self.timeout)
        except TimeoutError as e:
            raise HadesTimeout("The Hades lookup task has timed out") from e


hades_logs = LocalProxy(lambda: current_app.extensions['hades_logs'])
