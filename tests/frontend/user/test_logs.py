import unittest

from tests.factories import UserFactory, RoomLogEntryFactory, UserLogEntryFactory, \
    UserWithHostFactory

from hades_logs import HadesLogs
from tests import InvalidateHadesLogsMixin

from . import UserLogTestBase
from ...hades_logs import get_hades_logs_config


class AppWithoutHadesLogsTestCase(InvalidateHadesLogsMixin, UserLogTestBase):
    def test_only_warning_log_returned(self):
        # Multiple assertions in one method to avoid useless
        # setup/teardown which leads to 5s for this class
        hades_items = self.get_logs(logtype='hades')
        assert len(hades_items) == 1
        assert "logs cannot be displayed" in hades_items[0]['message'].lower()

        assert not self.get_logs(logtype='user')
        assert not self.get_logs(logtype='room')
        assert len(self.get_logs()) == 1


class RoomAndUserLogTestCase(UserLogTestBase):
    def create_factories(self):
        super().create_factories()
        self.relevant_user = UserFactory.create()
        self.room_log_entry = RoomLogEntryFactory(author=self.admin, room=self.relevant_user.room)
        self.user_log_entry = UserLogEntryFactory(author=self.admin, user=self.relevant_user)

    def assert_one_log(self, got_logs, expected_entry):
        assert len(got_logs) == 1
        item = got_logs[0]
        assert item['message'] == expected_entry.message
        assert item['user']['title'] == expected_entry.author.name

    def test_room_log_exists(self):
        items = self.get_logs(user_id=self.relevant_user.id, logtype='room')
        self.assert_one_log(items, self.room_log_entry)

    def test_user_log_exists(self):
        items = self.get_logs(user_id=self.relevant_user.id, logtype='user')
        self.assert_one_log(items, self.user_log_entry)

    def test_no_hades_log_exists(self):
        items = self.get_logs(user_id=self.relevant_user.id, logtype='hades')
        assert len(items) == 1
        item = items[0]
        assert " cannot be displayed" in item['message'].lower()
        assert " connected room" in item['message'].lower()


class IntegrationTestCase(InvalidateHadesLogsMixin, UserLogTestBase):
    """Frontend Tests for the endpoints utilizing live Hades Logs
    """
    def create_factories(self):
        super().create_factories()
        self.relevant_user = UserWithHostFactory(patched=True)
        self.other_user = UserFactory.create()
        self.room_log_entry = RoomLogEntryFactory(author=self.admin, room=self.relevant_user.room)
        self.user_log_entry = UserLogEntryFactory(author=self.admin, user=self.relevant_user)

    def create_app(self):
        app = super().create_app()

        # Setup dummy_tasks hades logs
        app.config.update(get_hades_logs_config())
        HadesLogs(app)

        return app

    def test_hades_logs_are_returned(self):
        logs = self.get_logs(user_id=self.relevant_user.id, logtype='hades')
        assert len(logs) == 4
        for log in logs:
            if "rejected" in log['message'].lower():
                continue
            assert "– groups: " in log['message'].lower()
            assert "tagged)" in log['message'].lower()

    def test_disconnected_user_emits_warning(self):
        logs = self.get_logs(self.other_user.id, logtype='hades')
        assert len(logs) == 1
        assert "are in a connected room" in logs[0]['message'].lower()
        assert "logs cannot be displayed" in logs[0]['message'].lower()
