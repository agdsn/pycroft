from pycroft.model._all import User
from tests import InvalidateHadesLogsMixin
from tests.fixtures import hades_logs, frontend_logs

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
    datasets = frozenset(frontend_logs.datasets)

    def setUp(self):
        super().setUp()
        self.UserLogEntryData = frontend_logs.logging.UserLogEntryData
        self.RoomLogEntryData = frontend_logs.logging.RoomLogEntryData
        login = self.UserLogEntryData.dummy_log_entry1.user.login
        # This is the user who has log entries
        self.relevant_user = User.q.filter_by(login=login).one()

    def test_room_log_exists(self):
        entry = self.RoomLogEntryData.dummy_log_entry1
        items = self.get_logs(user_id=self.relevant_user.id, logtype='room')
        self.assertEqual(len(items), 1)
        item = items[0]
        desired_message = self.RoomLogEntryData.dummy_log_entry1.message
        self.assertEqual(item['message'], desired_message)
        self.assertEqual(item['user']['title'], entry.author.name)

    def test_user_log_exists(self):
        entry = self.UserLogEntryData.dummy_log_entry1
        items = self.get_logs(user_id=self.relevant_user.id, logtype='user')
        self.assertEqual(len(items), 1)
        item = items[0]
        desired_message = self.UserLogEntryData.dummy_log_entry1.message
        self.assertEqual(item['message'], desired_message)
        self.assertEqual(item['user']['title'], entry.author.name)

    def test_no_hades_log_exists(self):
        items = self.get_logs(user_id=self.relevant_user.id, logtype='hades')
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertIn(" cannot be displayed", item['message'].lower())
        self.assertIn(" connected room", item['message'].lower())


class IntegrationTestCase(DummyHadesWorkerBase, UserLogTestBase):
    """Frontend Tests for the endpoints utilizing live Hades Logs
    """
    datasets = frozenset(hades_logs.datasets)

    def setUp(self):
        super().setUp()
        # We want the user from the UserHostData, not the dummy user
        # (which has no hosts)
        from tests.fixtures.dummy.host import UserHostData
        login = UserHostData.dummy.owner.login
        self.relevant_user = User.q.filter_by(login=login).one()

    def test_hades_logs_are_returned(self):
        logs = self.get_logs(user_id=self.relevant_user.id, logtype='hades')
        self.assertEqual(len(logs), 4)
        for log in logs:
            if "rejected" in log['message'].lower():
                continue
            self.assertIn("– groups: ", log['message'].lower())
            self.assertIn("tagged)", log['message'].lower())

    def test_disconnected_user_emits_warning(self):
        logs = self.get_logs(logtype='hades')
        self.assertEqual(len(logs), 1)
        self.assertIn("are in a connected room", logs[0]['message'].lower())
        self.assertIn("logs cannot be displayed", logs[0]['message'].lower())
