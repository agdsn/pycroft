import pytest
from flask import Flask

from hades_logs import HadesLogs
from tests.hades_logs import get_hades_logs_config


@pytest.fixture(scope='session')
def hades_logs_config():
    return get_hades_logs_config()


@pytest.fixture(scope='session')
def app(hades_logs_config):
    app = Flask('test')
    app.config.update(hades_logs_config)
    return app


@pytest.fixture(scope='session')
def app_longer_timeout(hades_logs_config):
    app = Flask('test')
    app.config.update(hades_logs_config | {'HADES_TIMEOUT': 15})
    return app


@pytest.fixture(scope='session')
def hades_logs(app):
    return HadesLogs(app)


@pytest.fixture(scope='session')
def valid_kwargs():
    return {'nasipaddress': '141.30.223.206', 'nasportid': 'C6'}
