import os
from unittest import TestCase

from flask import Flask

from hades_logs import HadesLogs

class DummyHadesWorkerBase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.BROKER_URL = os.environ['HADES_BROKER_URI']
        cls.BACKEND_URL = os.environ['HADES_RESULT_BACKEND_URI']

    @property
    def hades_logs_config(self):
        return {
            'HADES_CELERY_APP_NAME': 'dummy_tasks',
            'HADES_BROKER_URI': self.BROKER_URL,
            'HADES_RESULT_BACKEND_URI': self.BACKEND_URL,
            'HADES_ROUTING_KEY': None,
        }


class SimpleFlaskWithHadesLogsBase(DummyHadesWorkerBase):
    def setUp(self):
        super().setUp()
        self.app = Flask('test')
        self.app.config.update(self.hades_logs_config)
        self.hades_logs = HadesLogs(self.app)
        self.valid_kwargs = {'nasipaddress': '141.30.223.206', 'nasportid': 'C6'}

    def fetch_logs(self, *a, **kw):
        """Call :py:meth:`hades_logs.fetch_logs` and convert to list

        :rtype: list
        """
        return list(self.hades_logs.fetch_logs(*a, **kw))
