from flask import url_for

from pycroft.model.user import User
from tests.fixtures import permissions
from . import UserLogTestBase


class UserBlockingTestCase(UserLogTestBase):
    def test_blocking_and_unblocking_works(self):
        # Multiple assertions in one method to avoid useless
        # setup/teardown which leads to 5s for this class
        username = permissions.UserData.user3_user.login
        user = User.q.filter_by(login=username).one()

        user_show_endpoint = url_for("user.user_show", user_id=user.id)
        response = self.client.get(user_show_endpoint)
        self.assert200(response)

        response = self.client.post(url_for("user.suspend", user_id=user.id),
                                    data={'ends_at-unlimited': 'y',
                                          'reason': 'Ist doof'})
        self.assertRedirects(response, user_show_endpoint)

        show_response = self.assert_user_show_200(user.id)
        # this could be replaced with the new `assertMessageFlashed`
        self.assertIn("Nutzer gesperrt", show_response.data.decode('utf-8'))

        response = self.client.post(url_for("user.unblock", user_id=user.id),
                                    data={})
        self.assertRedirects(response, user_show_endpoint)
        show_response = self.assert_user_show_200(user.id)
        # this could be replaced with the new `assertMessageFlashed`
        self.assertIn("Nutzer entsperrt", show_response.data.decode('utf-8'))

    def assert_user_show_200(self, user_id):
        response = self.client.get(url_for("user.user_show", user_id=user_id))
        self.assert200(response)
        return response
