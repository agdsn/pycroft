import os
from unittest import TestCase

from flask import Flask

from hades_logs import HadesLogs


class ConfiguredHadesLogs(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.BROKER_URL = os.environ['HADES_BROKER_URI']
        cls.BACKEND_URL = os.environ['HADES_RESULT_BACKEND_URI']

    def setUp(self):
        super().setUp()
        self.app = Flask('test')
        self.app.config.update({
            'HADES_CELERY_APP_NAME': 'dummy_celery_worker',
            'HADES_BROKER_URI': self.BROKER_URL,
            'HADES_RESULT_BACKEND_URI': self.BACKEND_URL,
        })
        self.hades_logs = HadesLogs(self.app)

    def test_fetch_user_gives_constant(self):
        logs = self.hades_logs.fetch_logs(0, 0)
        self.assertEqual(len(logs), 3)
