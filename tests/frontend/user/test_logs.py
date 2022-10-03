import re
import typing as t

import pytest
from flask import url_for

from hades_logs import HadesLogs
from pycroft.model.session import Session
from pycroft.model.user import User
from tests.factories import UserFactory, RoomLogEntryFactory, \
    UserLogEntryFactory
from web import make_app, PycroftFlask
from ..assertions import TestClient
from ..fixture_helpers import prepare_app_for_testing, login_context
from ..legacy_base import InvalidateHadesLogsMixin, FrontendWithAdminTestBase
from ...hades_logs import get_hades_logs_config


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


def get_logs(user_id: int, client: TestClient, **kw) -> list[t.Any]:
    """Request a user's logs, assert validity, and pass on the returned log entries.

    By default, the logs are fetched for the user logging in.

    The following assertions are made:
      * The response code is 200
      * The response content_type contains ``"json"``
      * The response's JSON contains an ``"items"`` key

    :returns: ``response.json['items']``
    """
    response = client.assert_url_ok(
        url_for("user.user_show_logs_json", user_id=user_id, **kw)
    )
    assert "json" in response.content_type.lower()
    json = response.json
    assert json.get("items") is not None
    return json["items"]


GetLogs: t.TypeAlias = t.Callable[..., list[t.Any]]


class TestAppWithoutHadesLogs:
    @pytest.fixture(scope="class")
    def flask_app(self) -> PycroftFlask:
        return prepare_app_for_testing(make_app(hades_logs=False))

    @pytest.fixture(scope="class")
    def client(self, class_test_client: TestClient) -> TestClient:
        return class_test_client

    @pytest.fixture(scope="class", autouse=True)
    def admin_logged_in(self, admin: User, client: TestClient):
        with login_context(client, admin.login, "password"):
            yield

    @pytest.fixture(scope="class")
    def user(self, class_session: Session):
        user = UserFactory.create(with_host=True, patched=True)
        class_session.flush()
        return user

    @pytest.fixture(scope="class")
    def logs(self, user: User, client: TestClient) -> GetLogs:
        def _logs(**kwargs) -> list[t.Any]:
            return get_logs(user.id, client, **kwargs)

        return _logs

    @staticmethod
    def assert_hades_message(message: str):
        assert re.search(
            r"hadeslogs.*not configured.*logs cannot be displayed", message.lower()
        )

    def test_warning_log_tab_hades(self, logs: GetLogs):
        assert len(hades_items := logs(logtype="hades")) == 1
        self.assert_hades_message(hades_items[0]["message"])

    def test_warning_log_tab_user(self, logs: GetLogs):
        assert not logs(logtype="user")

    def test_warning_log_tab_room(self, logs: GetLogs):
        assert not logs(logtype="room")

    def test_warning_log_tab_all(self, logs: GetLogs):
        assert len(logs := logs()) == 1
        self.assert_hades_message(logs[0]["message"])


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
        self.relevant_user = UserFactory(with_host=True, patched=True)
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
