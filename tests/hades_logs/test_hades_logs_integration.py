import os
from unittest import TestCase

from flask import Flask

from hades_logs import HadesLogs, HadesTimeout


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
        self.valid_kwargs = {'nasipaddress': '141.30.223.206', 'nasportid': 'C6'}

    def fetch_logs(self, *a, **kw):
        """Call :py:meth:`hades_logs.fetch_logs` and convert to list

        :rtype: list
        """
        return list(self.hades_logs.fetch_logs(*a, **kw))

    def test_nonexistent_port_has_no_logs(self):
        logs = self.fetch_logs(nasipaddress='', nasportid='')
        self.assertEqual(logs, [])

    def test_fake_switch_correct_log_entries(self):
        logs = self.fetch_logs(**self.valid_kwargs)
        self.assertEqual(len(logs), 4)

    def test_limit_works(self):
        logs = self.fetch_logs(limit=0, **self.valid_kwargs)
        self.assertEqual(len(logs), 0)

        logs = self.fetch_logs(limit=3, **self.valid_kwargs)
        self.assertEqual(len(logs), 3)

        logs = self.fetch_logs(limit=100, **self.valid_kwargs)
        self.assertEqual(len(logs), 4)

    def test_long_task_triggers_timeout_per_default(self):
        with self.assertRaises(HadesTimeout):
            self.fetch_logs(nasipaddress='', nasportid='magic_sleep')

    def test_longer_timeout_allows_long_task_to_finish(self):
        self.app.config.update({'HADES_TIMEOUT': 15})
        self.hades_logs = HadesLogs(self.app)
        try:
            tasks = self.fetch_logs(nasipaddress='', nasportid='magic_sleep')
        except HadesTimeout:
            self.fail("HadesTimeout triggered even with significantly longer timeout")
        else:
            self.assertEqual(tasks, [])
