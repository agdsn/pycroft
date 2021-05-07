import pytest

from hades_logs import HadesLogs, HadesTimeout
from hades_logs.parsing import RadiusLogEntry


class TestConfiguredHadesLogs:
    def test_nonexistent_port_has_no_logs(self, hades_logs):
        logs = list(hades_logs.fetch_logs(nasipaddress='', nasportid=''))
        assert logs == []

    def test_fake_switch_correct_log_entries(self, hades_logs, valid_kwargs):
        logs = list(hades_logs.fetch_logs(**valid_kwargs))
        assert len(logs) == 4

    @pytest.mark.parametrize('limit, expected', [
        (0, 0), (3, 3), (100, 4),
    ])
    def test_limit_works(self, hades_logs, limit, expected, valid_kwargs):
        logs = list(hades_logs.fetch_logs(limit=limit, **valid_kwargs))
        assert len(logs) == expected

    @pytest.mark.slow
    def test_long_task_triggers_timeout_per_default(self, hades_logs):
        with pytest.raises(HadesTimeout):
            hades_logs.fetch_logs(nasipaddress='', nasportid='magic_sleep')

    @pytest.mark.slow
    def test_longer_timeout_allows_long_task_to_finish(self, app_longer_timeout):
        hades_logs = HadesLogs(app_longer_timeout)
        try:
            tasks = list(hades_logs.fetch_logs(nasipaddress='', nasportid='magic_sleep'))
        except HadesTimeout:
            pytest.fail("HadesTimeout triggered even with significantly longer timeout")
        else:
            assert tasks == []


class TestSpecificLogs:
    @pytest.fixture(scope='class')
    def logs(self, hades_logs, valid_kwargs):
        return list(hades_logs.fetch_logs(**valid_kwargs))

    @pytest.fixture(scope='class')
    def accepted_logs(self, logs):
        return [e for e in logs if e.accepted]

    def test_logs_have_correct_instances(self, logs):
        for log in logs:
            assert isinstance(log, RadiusLogEntry)

    def test_correct_number_of_logs_are_accepted(self, accepted_logs):
        assert len(accepted_logs) == 3

    def test_every_log_has_a_mac(self, logs):
        for log in logs:
            assert len(log.mac) == len("00:de:ad:be:ef:00")

    def test_every_accepted_log_has_one_vlan(self, accepted_logs):
        for log in accepted_logs:
            assert len(log.vlans) == 1
