import unittest

from tests.factories import UserFactory, RoomLogEntryFactory, UserLogEntryFactory, \
    UserWithHostFactory

from hades_logs import HadesLogs
from tests import InvalidateHadesLogsMixin

from . import UserLogTestBase
from ...hades_logs import DummyHadesWorkerBase


class AppWithoutHadesLogsTestCase(InvalidateHadesLogsMixin, UserLogTestBase):
    def test_only_warning_log_returned(self):
        # Multiple assertions in one method to avoid useless
        # setup/teardown which leads to 5s for this class
        hades_items = self.get_logs(logtype='hades')
        self.assertEqual(len(hades_items), 1)
        self.assertIn("logs cannot be displayed", hades_items[0]['message'].lower())

        self.assertFalse(self.get_logs(logtype='user'))
        self.assertFalse(self.get_logs(logtype='room'))
        self.assertEqual(len(self.get_logs()), 1)


class RoomAndUserLogTestCase(UserLogTestBase):
    def create_factories(self):
        super().create_factories()
        self.relevant_user = UserFactory.create()
        self.room_log_entry = RoomLogEntryFactory(author=self.admin, room=self.relevant_user.room)
        self.user_log_entry = UserLogEntryFactory(author=self.admin, user=self.relevant_user)

    def assert_one_log(self, got_logs, expected_entry):
        self.assertEqual(len(got_logs), 1)
        item = got_logs[0]
        self.assertEqual(item['message'], expected_entry.message)
        self.assertEqual(item['user']['title'], expected_entry.author.name)

    def test_room_log_exists(self):
        items = self.get_logs(user_id=self.relevant_user.id, logtype='room')
        self.assert_one_log(items, self.room_log_entry)

    def test_user_log_exists(self):
        items = self.get_logs(user_id=self.relevant_user.id, logtype='user')
        self.assert_one_log(items, self.user_log_entry)

    def test_no_hades_log_exists(self):
        items = self.get_logs(user_id=self.relevant_user.id, logtype='hades')
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertIn(" cannot be displayed", item['message'].lower())
        self.assertIn(" connected room", item['message'].lower())


class IntegrationTestCase(InvalidateHadesLogsMixin, DummyHadesWorkerBase, UserLogTestBase):
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
        app.config.update(self.hades_logs_config)
        HadesLogs(app)

        return app

    def test_hades_logs_are_returned(self):
        logs = self.get_logs(user_id=self.relevant_user.id, logtype='hades')
        self.assertEqual(len(logs), 4)
        for log in logs:
            if "rejected" in log['message'].lower():
                continue
            self.assertIn("– groups: ", log['message'].lower())
            self.assertIn("tagged)", log['message'].lower())

    def test_disconnected_user_emits_warning(self):
        logs = self.get_logs(self.other_user.id, logtype='hades')
        self.assertEqual(len(logs), 1)
        self.assertIn("are in a connected room", logs[0]['message'].lower())
        self.assertIn("logs cannot be displayed", logs[0]['message'].lower())
