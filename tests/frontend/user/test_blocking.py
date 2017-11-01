from flask import url_for

from pycroft.model.user import User
from tests.fixtures import permissions
from . import UserLogTestBase


class UserBlockingTestCase(UserLogTestBase):
    def setUp(self):
        super().setUp()
        username = permissions.UserData.user3_user.login
        self.test_user_id = User.q.filter_by(login=username).one().id

    def test_blocking_and_unblocking_works(self):
        user_show_endpoint = url_for("user.user_show", user_id=self.test_user_id)
        response = self.client.get(user_show_endpoint)
        self.assert200(response)

        response = self.client.post(url_for("user.suspend", user_id=self.test_user_id),
                                    data={'ends_at-unlimited': 'y',
                                          'reason': 'Ist doof'})
        self.assertRedirects(response, user_show_endpoint)
        self.assert_message_flashed("Nutzer gesperrt", 'success')

        response = self.client.post(url_for("user.unblock", user_id=self.test_user_id))
        self.assertRedirects(response, user_show_endpoint)
        self.assert_message_flashed("Nutzer entsperrt", 'success')

    def test_unblocked_user_cannot_be_unblocked(self):
        response = self.client.post(url_for("user.unblock", user_id=self.test_user_id))
        self.assert404(response)
        self.assert_message_substr_flashed("ist nicht gesperrt!", category='error')
