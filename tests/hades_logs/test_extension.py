import logging
from contextlib import contextmanager

import pytest

from flask import Flask
from kombu.exceptions import OperationalError

from hades_logs import HadesLogs, hades_logs
from hades_logs.exc import HadesOperationalError


@contextmanager
def assert_unconfigured(caplog, level=logging.WARNING):
    with pytest.raises(KeyError) as exc_cm, \
         caplog.at_level(level, logger='hades_logs'):
        yield

    assert 'missing config ' in str(exc_cm.value).lower()

    assert len(caplog.records) == 1
    assert "missing config" in caplog.text.lower()


def test_plain_init_works():
    # noinspection PyBroadException
    try:
        HadesLogs()
    except Exception:  # pylint: disable=broad-except
        pytest.fail("Bare init didn't work")


class TestUnconfiguredInitialization:
    @pytest.fixture(scope='class')
    def app(self):
        return Flask('test')

    def test_init_initializes_app(self, app, caplog):
        with assert_unconfigured(caplog):
            HadesLogs(app)

    def test_init_app_initializes_app(self, app, caplog):
        logs = HadesLogs()
        with assert_unconfigured(caplog):
            logs.init_app(app)

    def test_proxy_object_inaccessible(self):
        with pytest.raises(RuntimeError) as cm:
            _ = hades_logs.app
        assert "working outside of application context" in str(cm.value).lower()


class ConfiguredFlaskAppTestBase:
    @pytest.fixture(scope='module')
    def app(self):
        """Provide a flask app with enough config for ``HadesLogs``"""
        app = Flask('testapp')
        app.config.update({
            'HADES_CELERY_APP_NAME': 'test',
            'HADES_BROKER_URI': 'rpc://broker/',
            'HADES_RESULT_BACKEND_URI': 'rpc://backend/',
            })
        return app


class TestConfiguredInitialization(ConfiguredFlaskAppTestBase):
    """The flask app is configured, but ``HadesLogs`` not registered"""

    @contextmanager
    def assert_registers_extension(self, app, caplog):
        with caplog.at_level(logging.INFO, logger='hades_logs'):
            yield

        assert len(caplog.records) == 1
        assert "initialization complete" in caplog.text.lower()
        assert 'hades_logs' in app.extensions

    def test_init_initializes_app(self, app, caplog):
        with self.assert_registers_extension(app, caplog):
            HadesLogs(app)

    def test_init_app_initializes_app(self, app, caplog):
        l = HadesLogs()
        with self.assert_registers_extension(app, caplog):
            l.init_app(app)

    def test_proxy_object_accessible(self, app):
        try:
            with app.app_context():
                # noinspection PyStatementEffect
                hades_logs  # noqa: B018
        except RuntimeError:
            pytest.fail("`hades_logs` inaccessible although in app context")


class TestRegisteredExtension(ConfiguredFlaskAppTestBase):
    """``HadesLogs`` is now registered to the app"""
    @pytest.fixture(scope='class')
    def hades_logs(self, app):
        return HadesLogs(app)

    def test_celery_app_name_passed(self, hades_logs, app):
        assert hades_logs.celery.main == app.config['HADES_CELERY_APP_NAME']

    def test_celery_broker_url_passed(self, hades_logs, app):
        # In celery 4.0, this is `conf.broker_url`
        assert hades_logs.celery.conf['BROKER_URL'] == app.config['HADES_BROKER_URI']

    def localhost(self, hades_logs, app):
        assert hades_logs.celery.conf.result_localhost == app.config['HADES_RESULT_BACKEND_URI']

    def test_timeout_set(self, hades_logs):
        assert hades_logs.timeout == 5


class TestManualTimeoutConfigured(ConfiguredFlaskAppTestBase):
    """Configure a manual timeout and see it was passed"""
    @pytest.fixture(scope='class')
    def hades_logs(self, app):
        app.config['HADES_TIMEOUT'] = 10
        return HadesLogs(app)

    def test_timeout_passed(self, hades_logs):
        assert hades_logs.timeout == 10


class TestTaskCreated(ConfiguredFlaskAppTestBase):
    """Provide a task created by :py:meth`create_task`"""
    @pytest.fixture(scope='class')
    def hades_logs(self, app):
        return HadesLogs(app)

    @pytest.fixture(scope='class')
    def task(self, hades_logs):
        return hades_logs.create_task('taskname', 'foo', bar='baz')

    def test_task_bound_to_app(self, task, hades_logs):
        assert task.app is hades_logs.celery

    def test_task_name_correct(self, task):
        # In celery 4.0, this is `self.task.name`
        assert task.task == 'test.taskname'

    def test_task_args_passed(self, task):
        assert task.args == ('foo',)

    def test_task_kwargs_passed(self, task):
        assert task.kwargs == {'bar': 'baz'}


class TestCorrectURIsConfigured:
    """Provides ``HadesLogs`` with syntactically correct URIs"""
    @pytest.fixture(scope='class')
    def hades_logs(self):
        app = Flask('test')
        app.config.update({
            'HADES_CELERY_APP_NAME': 'test',
            # intentionally wrong urls to trigger `OperationalError`s
            'HADES_BROKER_URI': 'amqp://localhost:5762/',
            'HADES_RESULT_BACKEND_URI': 'rpc://localhost:5762/',
        })
        return HadesLogs(app)

    def test_empty_task_raises_operational_error(self, hades_logs):
        # This throws an `OperationalError` as there is no `HadesLogs` around to
        # wrap it into a `HadesOperationalError`.
        with pytest.raises(OperationalError):
            hades_logs.celery.signature('').apply_async().wait()

    def test_fetch_logs_logs_and_raises_connection_refused(self, hades_logs, caplog):
        with pytest.raises(HadesOperationalError), \
             caplog.at_level(logging.INFO, logger='hades_logs'):
            # noinspection PyTypeChecker
            hades_logs.fetch_logs(None, None)

        assert len(caplog.records) == 1
        assert "waiting for task" in caplog.text.lower()
