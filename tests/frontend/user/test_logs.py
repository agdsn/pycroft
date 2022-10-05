import re
import typing as t

import pytest
from flask import url_for

from hades_logs import HadesLogs
from pycroft.model.logging import UserLogEntry, RoomLogEntry
from pycroft.model.session import Session
from pycroft.model.user import User
from tests.factories import UserFactory, RoomLogEntryFactory, \
    UserLogEntryFactory
from web import make_app, PycroftFlask
from ..assertions import TestClient
from ..fixture_helpers import prepare_app_for_testing, login_context
from ...hades_logs import get_hades_logs_config


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
    def app(self) -> PycroftFlask:
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


@pytest.mark.usefixtures("admin")
class TestRoomAndUserLogDisplay:
    @pytest.fixture(scope="class", autouse=True)
    def admin_logged_in(self, admin, class_test_client: TestClient):
        with login_context(class_test_client, admin.login, "password"):
            yield

    @pytest.fixture(scope="class")
    def user(self, class_session: Session) -> User:
        return UserFactory.create()

    @pytest.fixture(scope="class", autouse=True)
    def room_log_entry(
        self, admin: User, class_session: Session, user: User
    ) -> RoomLogEntry:
        return RoomLogEntryFactory(author=admin, room=user.room)

    @pytest.fixture(scope="class", autouse=True)
    def user_log_entry(
        self, admin: User, class_session: Session, user: User
    ) -> UserLogEntry:
        return UserLogEntryFactory(author=admin, user=user)

    @pytest.fixture(scope="class")
    def logs(self, user, class_test_client: TestClient) -> GetLogs:
        def _logs(**kwargs) -> list[t.Any]:
            return get_logs(user.id, class_test_client, **kwargs)

        return _logs

    @staticmethod
    def assert_one_log(got_logs, expected_entry):
        assert len(got_logs) == 1
        item = got_logs[0]
        assert item['message'] == expected_entry.message
        assert item['user']['title'] == expected_entry.author.name

    def test_room_log_exists(self, logs: GetLogs, room_log_entry: RoomLogEntry):
        items = logs(logtype="room")
        self.assert_one_log(items, room_log_entry)

    def test_user_log_exists(self, logs: GetLogs, user_log_entry: UserLogEntry):
        items = logs(logtype="user")
        self.assert_one_log(items, user_log_entry)

    def test_no_hades_log_exists(self, logs: GetLogs):
        items = logs(logtype="hades")
        assert len(items) == 1
        item = items[0]
        assert " cannot be displayed" in item['message'].lower()
        assert " connected room" in item['message'].lower()


class TestDummyHadesLogs:
    """Frontend Tests for the endpoints utilizing live Hades Logs
    """
    @pytest.fixture(scope="class", autouse=True)
    def user(self, class_session):
        return UserFactory.create(with_host=True, patched=True)

    @pytest.fixture(scope="class")
    def other_user(self, class_session):
        return UserFactory.create()

    @pytest.fixture(scope="class", autouse=True)
    def user_and_log_entries(self, class_session: Session, admin: User, user: User) -> None:
        RoomLogEntryFactory.create(author=admin, room=user.room)
        UserLogEntryFactory.create(author=admin, user=user)
        class_session.flush()

    @pytest.fixture(scope="class")
    def app(self) -> PycroftFlask:
        """Overridden flask app with `HadesLogs` pointing at stub RPC instance"""
        app = prepare_app_for_testing(make_app(hades_logs=False))
        dummy_config = get_hades_logs_config()
        app.config.update(dummy_config)
        HadesLogs(app)
        return app

    @pytest.fixture(scope="class", autouse=True)
    def admin_logged_in(self, admin: User, class_test_client: TestClient):
        with login_context(class_test_client, admin.login, "password"):
            yield

    @pytest.fixture(scope="class")
    def logs(self, user: User, class_test_client: TestClient) -> GetLogs:
        def _logs(**kwargs) -> list[t.Any]:
            user_id = kwargs.pop("user_id", None) or user.id
            return get_logs(user_id, class_test_client, **kwargs)

        return _logs

    def test_hades_logs_are_returned(self, logs: GetLogs):
        assert len(logs := logs(logtype="hades")) == 4
        for log in logs:
            if "rejected" in log['message'].lower():
                continue
            assert "– groups: " in log['message'].lower()
            assert "tagged)" in log['message'].lower()

    def test_disconnected_user_emits_warning(self, logs: GetLogs, other_user: User):
        assert len(logs := logs(user_id=other_user.id, logtype="hades")) == 1
        assert "are in a connected room" in logs[0]['message'].lower()
        assert "logs cannot be displayed" in logs[0]['message'].lower()
