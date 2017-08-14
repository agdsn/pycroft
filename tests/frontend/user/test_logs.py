from unittest import TestCase

from flask import url_for

from tests import FrontendDataTestBase, InvalidateHadesLogsMixin
from tests.fixtures.permissions import UserData, MembershipData, PropertyData
from tests.fixtures.config import ConfigData


class UserShowTestBase(FrontendDataTestBase):
    """Test base providing access to `user_show`

    The user being logged in is :py:cls:`UserData.user1_admin`.
    """
    datasets = [MembershipData, PropertyData, ConfigData]

    def setUp(self):
        self.login = UserData.user1_admin.login
        self.password = UserData.user1_admin.password
        super().setUp()


class AppWithoutHadesLogsTestCase(InvalidateHadesLogsMixin, UserShowTestBase):
    def get_logs(self, **kw):
        """Request the logs, assert validity, and return the response.

        The following assertions are made:
          * The response code is 200
          * The response content_type contains ``"json"``
          * The response's JSON contains an ``"items"`` key

        :returns: ``response.json['items']``
        """
        log_endpoint = url_for('user.user_show_logs_json',
                               user_id=self.user_id,
                               **kw)
        response = self.assert_response_code(log_endpoint, code=200)
        self.assertIn("json", response.content_type.lower())
        json = response.json
        self.assertIsNotNone(json.get('items'))
        return json['items']


    def test_warning_log_returned(self):
        items = self.get_logs(type='hades')
        self.assertEqual(len(items), 1)

    def test_no_user_logs(self):
        items = self.get_logs(type='user')
        self.assertFalse(len(items))

    def test_no_room_logs(self):
        items = self.get_logs(type='room')
        self.assertFalse(len(items))
