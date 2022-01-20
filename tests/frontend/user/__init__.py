from flask import url_for

from tests.frontend.legacy_base import FrontendWithAdminTestBase
from tests.factories import RoomFactory, SubnetFactory, PatchPortFactory


class UserLogTestBase(FrontendWithAdminTestBase):
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
        assert "json" in response.content_type.lower()
        json = response.json
        assert json.get('items') is not None
        return json['items']


class UserFrontendTestBase(FrontendWithAdminTestBase):
    def create_factories(self):
        super().create_factories()
        self.room = RoomFactory()
        self.subnet = SubnetFactory()
        self.patch_port = PatchPortFactory(room=self.room, patched=True,
                                           switch_port__switch__host__owner=self.admin)
        # 2. A pool of default vlans so an IP can be found
        self.patch_port.switch_port.default_vlans.append(self.subnet.vlan)
