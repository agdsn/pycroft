from contextlib import contextmanager
from unittest import TestCase

from flask import Flask

from hades_logs import HadesLogs, hades_logs
from hades_logs.exc import HadesOperationalError


class UnconfiguredInitializationTestCase(TestCase):
    def setUp(self):
        super().setUp()
        class _app:
            extensions = {}
            config = {}
        self.app = _app

    @contextmanager
    def assert_unconfigured(self):
        with self.assertRaises(KeyError) as cm:
            yield
        self.assertIn('missing config ', str(cm.exception).lower())

    def test_plain_init_works(self):
        try:
            HadesLogs()
        except Exception:  # pylint: disable=broad-except
            self.fail("Bare init didn't work")

    def test_init_initializes_app(self):
        with self.assert_unconfigured():
            HadesLogs(self.app)

    def test_init_app_initializes_app(self):
        l = HadesLogs()
        with self.assert_unconfigured():
            l.init_app(self.app)

    def test_proxy_object_inaccessible(self):
        with self.assertRaises(RuntimeError) as cm:
            hades_logs.app  # pylint: disable=pointless-statement
        self.assertIn("working outside of application context",
                      str(cm.exception).lower())


class ConfiguredFlaskAppTestBase(TestCase):
    """Provide a flask app with enough config for ``HadesLogs``"""
    def setUp(self):
        super().setUp()
        self.app = Flask('testapp')
        self.app.config.update({
            'HADES_CELERY_APP_NAME': 'test',
            'HADES_BROKER_URI': 'rpc://broker/',
            'HADES_RESULT_BACKEND_URI': 'rpc://backend/',
        })


class ConfiguredInitializationTestCase(ConfiguredFlaskAppTestBase):
    """The flask app is configured, but ``HadesLogs`` not registered"""
    def assert_extension_registered(self, app):
        self.assertIn('hades_logs', app.extensions)

    def test_init_initializes_app(self):
        HadesLogs(self.app)
        self.assert_extension_registered(self.app)

    def test_init_app_initializes_app(self):
        l = HadesLogs()
        l.init_app(self.app)
        self.assert_extension_registered(self.app)

    def test_proxy_object_accessible(self):
        try:
            with self.app.app_context():
                hades_logs  # pylint: disable=pointless-statement
        except RuntimeError:
            self.fail("`hades_logs` inaccessible although in app context")


class RegisteredExtensionTestCase(ConfiguredFlaskAppTestBase):
    """``HadesLogs`` is now registered to the app"""
    def setUp(self):
        super().setUp()
        self.hades_logs = HadesLogs(self.app)

    def test_celery_app_name_passed(self):
        self.assertEqual(self.hades_logs.celery.main,
                         self.app.config['HADES_CELERY_APP_NAME'])

    def test_celery_broker_url_passed(self):
        # In celery 4.0, this is `conf.broker_url`
        self.assertEqual(self.hades_logs.celery.conf['BROKER_URL'],
                         self.app.config['HADES_BROKER_URI'])

    def localhost(self):
        self.assertEqual(self.hades_logs.celery.conf.result_localhost,
                         self.app.config['HADES_RESULT_BACKEND_URI'])

    def test_timeout_set(self):
        self.assertEqual(self.hades_logs.timeout, 5)


class ManualTimeoutConfiguredTestCase(ConfiguredFlaskAppTestBase):
    """Configure a manual timeout and see it was passed"""
    def setUp(self):
        super().setUp()
        self.app.config['HADES_TIMEOUT'] = 10
        self.hades_logs = HadesLogs(self.app)

    def test_timeout_passed(self):
        self.assertEqual(self.hades_logs.timeout, 10)


class TaskCreatedTestCase(ConfiguredFlaskAppTestBase):
    """Provide a task created by :py:meth`create_task`"""
    def setUp(self):
        super().setUp()
        self.hades_logs = HadesLogs(self.app)
        self.task = self.hades_logs.create_task('taskname', 'foo', bar='baz')

    def test_task_bound_to_app(self):
        self.assertTrue(self.task.app is self.hades_logs.celery)

    def test_task_name_correct(self):
        # In celery 4.0, this is `self.task.name`
        self.assertEqual(self.task.task, 'test.taskname')

    def test_task_args_passed(self):
        self.assertEqual(self.task.args, ('foo',))

    def test_task_kwargs_passed(self):
        self.assertEqual(self.task.kwargs, {'bar': 'baz'})


class CorrectURIsConfiguredTestCase(TestCase):
    """Provides ``HadesLogs`` with syntactically correct URIs"""
    def setUp(self):
        super().setUp()
        self.app = Flask('test')
        self.app.config.update({
            'HADES_CELERY_APP_NAME': 'test',
            'HADES_BROKER_URI': 'amqp://localhost:5762/',
            'HADES_RESULT_BACKEND_URI': 'rpc://localhost:5762/',
        })
        self.hades_logs = HadesLogs(self.app)

    def test_empty_task_raises_operational_error(self):
        # This throws an OSError as there is no `HadesLogs` around to
        # catch it.
        with self.assertRaises(OSError) as cm:
            self.hades_logs.celery.signature('').apply_async().wait()

    def test_fetch_logs_raises_connection_refused(self):
        with self.assertRaises(HadesOperationalError) as cm:
            self.hades_logs.fetch_logs(None, None)
