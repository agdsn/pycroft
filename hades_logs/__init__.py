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


def build_hades_celery_app(app_name, broker_uri, backend_uri):
    pass  # TODO: install celery and build with Celery()


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

        build_hades_celery_app(app_name, broker_uri, backend_uri)


hades_logs = LocalProxy(lambda: current_app.extensions['hades_logs'])
