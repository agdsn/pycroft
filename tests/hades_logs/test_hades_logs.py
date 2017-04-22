from contextlib import contextmanager
from unittest import TestCase

from flask import Flask

from hades_logs import HadesLogs, hades_logs


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


class BadUriTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.app = Flask('testapp')
        self.app.config.update({
            'HADES_CELERY_APP_NAME': 'test',
            'HADES_BROKER_URI': 'notauri',
            'HADES_RESULT_BACKEND_URI': 'notauri',
        })

    def test_initialization_fails(self):
        # here should be some test that verifies `HadesLogs` tries to
        # init a celery app.
        pass


class ConfiguredInitializationTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.app = Flask('testapp')
        self.app.config.update({
            'HADES_CELERY_APP_NAME': 'test',
            'HADES_BROKER_URI': 'rpc:///',
            'HADES_RESULT_BACKEND_URI': 'rpc:///',
        })

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
