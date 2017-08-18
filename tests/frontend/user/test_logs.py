from unittest import TestCase

from flask import url_for

from pycroft.model._all import User
from tests import FrontendDataTestBase, InvalidateHadesLogsMixin
from tests.fixtures import permissions
from tests.fixtures import hades_logs, frontend_logs


class UserLogTestBase(FrontendDataTestBase):
    """Test base providing access to `user_show`

    The user being logged in is :py:cls:`UserData.user1_admin`.
    """
    datasets = frozenset(permissions.datasets)

    def setUp(self):
        self.login = permissions.UserData.user1_admin.login
        self.password = permissions.UserData.user1_admin.password
        super().setUp()


    def get_logs(self, user_id=None, **kw):
        """Request the logs, assert validity, and return the response.

        By default, the logs are fetched for the user logging in.

        The following assertions are made:
          * The response code is 200
          * The response content_type contains ``"json"``
          * The response's JSON contains an ``"items"`` key

        :returns: ``response.json['items']``
        """
        if user_id is None:
            user_id = self.user_id
        log_endpoint = url_for('user.user_show_logs_json',
                               user_id=user_id,
                               **kw)
        response = self.assert_response_code(log_endpoint, code=200)
        self.assertIn("json", response.content_type.lower())
        json = response.json
        self.assertIsNotNone(json.get('items'))
        return json['items']


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


class UserWithDummyHadesLogsTestCase(UserLogTestBase):
    datasets = frozenset(hades_logs.datasets)

    def setUp(self):
        super().setUp()
        # We want the user from the UserHostData, not the dummy user
        # (which has no hosts)
        from tests.fixtures.dummy.host import UserHostData
        login = UserHostData.dummy.owner.login
        self.relevant_user = User.q.filter_by(login=login).one()

    def test_dummy_hades_logs_are_returned(self):
        logs = self.get_logs(user_id=self.relevant_user.id, logtype='hades')
        self.assertEqual(len(logs), 2)
        for log in logs:
            self.assertIn("– groups: ", log['message'].lower())
            self.assertIn("tagged)", log['message'].lower())
