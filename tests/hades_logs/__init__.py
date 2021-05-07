import os
from unittest import TestCase

import pytest
from flask import Flask

from hades_logs import HadesLogs


def get_hades_logs_config():
    return {
        'HADES_CELERY_APP_NAME': 'dummy_tasks',
        'HADES_BROKER_URI': os.environ['HADES_BROKER_URI'],
        'HADES_RESULT_BACKEND_URI': os.environ['HADES_RESULT_BACKEND_URI'],
        'HADES_ROUTING_KEY': None,
    }


class DummyHadesWorkerBase(TestCase):
    """Used for configuring the `Flask` app for `HadesLogs`,
    as well as in the user integration test"""
    @property
    def hades_logs_config(self):
        return get_hades_logs_config()


def fetch_logs(hades_logs, *a, **kw):
    """Call :py:meth:`hades_logs.fetch_logs` and convert to list

    :rtype: list
    """
    return list(hades_logs.fetch_logs(*a, **kw))
