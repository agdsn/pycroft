from hades_logs import HadesLogs, HadesTimeout
from hades_logs.parsing import RadiusLogEntry
from . import SimpleFlaskWithHadesLogsBase


class ConfiguredHadesLogs(SimpleFlaskWithHadesLogsBase):
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


class SpecificLogsTestCase(SimpleFlaskWithHadesLogsBase):
    def setUp(self):
        super().setUp()
        self.logs = self.fetch_logs(**self.valid_kwargs)
        self.accepted_logs = [e for e in self.logs if e.accepted]

    def test_logs_have_correct_instances(self):
        for log in self.logs:
            self.assertIsInstance(log, RadiusLogEntry)

    def test_correct_number_of_logs_are_accepted(self):
        self.assertEqual(len(self.accepted_logs), 3)

    def test_every_log_has_a_mac(self):
        for log in self.logs:
            self.assertEqual(len(log.mac), len("00:de:ad:be:ef:00"))

    def test_every_accepted_log_has_one_vlan(self):
        for log in self.accepted_logs:
            self.assertEqual(len(log.vlans), 1)
