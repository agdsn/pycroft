import contextlib

import pytest
from flask import url_for
from sqlalchemy.orm import Session

from pycroft import Config
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.user import User
from pycroft.model.webstorage import WebStorage
from tests.factories import (
    UserFactory,
    RoomFactory,
)
from ..assertions import TestClient
from ...factories.address import AddressFactory


pytestmark = pytest.mark.usefixtures("admin_logged_in")


@pytest.fixture(scope="module")
def room(module_session: Session) -> Room:
    room = RoomFactory.create(patched_with_subnet=True)
    module_session.add(room)
    module_session.flush()
    return room


@pytest.mark.usefixtures("session")
class TestUserViewingPages:
    def test_user_overview_access(self, test_client: TestClient):
        test_client.assert_ok("user.overview")

    def test_user_viewing_himself(self, test_client: TestClient, admin):
        test_client.assert_url_ok(url_for("user.user_show", user_id=admin.id))

    def test_user_search_access(self, test_client: TestClient):
        test_client.assert_ok("user.search")


@pytest.mark.usefixtures("session")
class TestInhabitingUser:
    @pytest.fixture(scope="class")
    def user(self, class_session: Session, config: Config) -> User:
        user = UserFactory.create(
            with_host=True,
            with_membership=True,
            membership__includes_today=True,
            membership__group=config.member_group,
        )
        class_session.flush()
        return user

    def test_blocking_and_unblocking_works(self, test_client: TestClient, user: User):
        user_show_endpoint = url_for("user.user_show", user_id=user.id)
        test_client.assert_url_ok(user_show_endpoint)

        with test_client.flashes_message("Nutzer gesperrt", "success"):
            test_client.assert_url_redirects(
                url_for("user.block", user_id=user.id),
                expected_location=user_show_endpoint,
                method="post",
                data={"ends_at-unlimited": "y", "reason": "Ist doof"},
            )

        with test_client.flashes_message("Nutzer entsperrt", "success"):
            test_client.assert_url_redirects(
                url_for("user.unblock", user_id=user.id),
                expected_location=user_show_endpoint,
                method="post",
            )

    def test_user_cannot_be_moved_back_in(self, test_client: TestClient, user: User):
        # attempt to move the user back in
        with test_client.flashes_message(
            f"Nutzer {user.id} ist nicht ausgezogen!", category="error"
        ):
            test_client.assert_url_response_code(
                url_for("user.move_in", user_id=user.id),
                code=404,
                method="post",
                data={
                    # Will be serialized to str implicitly
                    "building": user.room.building.id,
                    "level": user.room.level,
                    "room_number": user.room.number,
                    "mac": "00:de:ad:be:ef:00",
                    "birthday": "1990-01-01",
                    "when": session.utcnow().date(),
                },
            )

    def test_user_moved_out_correctly(self, test_client: TestClient, user: User):
        with test_client.flashes_message("Benutzer ausgezogen.", "success"):
            test_client.assert_url_redirects(
                url_for("user.move_out", user_id=user.id),
                method="post",
                data={
                    # Will be serialized to str implicitly
                    "comment": "Test Comment",
                    "end_membership": True,
                    "now": False,
                    "when": session.utcnow().date(),
                },
                expected_location=url_for("user.user_show", user_id=user.id),
            )
        # TODO: Test whether everything has been done on the library side!


@pytest.mark.usefixtures("session")
class TestUserMovedOut:
    @pytest.fixture(scope="class")
    def user(self, class_session: Session) -> User:
        user = UserFactory.create(room=None, address=AddressFactory())
        class_session.flush()
        return user

    def test_user_cannot_be_moved_out(self, test_client: TestClient, user: User):
        # user.room = None  # ???
        with test_client.flashes_message(
            f"Nutzer {user.id} ist aktuell nirgends eingezogen!", category="error"
        ):
            test_client.assert_url_response_code(
                url_for("user.move_out", user_id=user.id),
                method="post",
                data={"now": True, "comment": "Ist doof"},
                code=404,
            )

    def test_static_datasheet(self, test_client: TestClient, user: User):
        response = test_client.assert_url_ok(
            url_for("user.static_datasheet", user_id=user.id)
        )
        assert response.data.startswith(b"%PDF")
        headers = response.headers
        assert headers.get("Content-Type") == "application/pdf"
        assert (
            headers.get("Content-Disposition")
            == f"inline; filename=user_sheet_plain_{user.id}.pdf"
        )

    def test_password_reset(self, test_client: TestClient, user: User):
        with test_client.flashes_message(
            "Passwort erfolgreich zurückgesetzt.", category="success"
        ):
            test_client.post(url_for("user.reset_password", user_id=user.id))

        # access user_sheet
        response = test_client.assert_ok("user.user_sheet")
        assert WebStorage.q.count() == 1
        assert response.headers.get('Content-Type') == "application/pdf"
        assert response.headers.get('Content-Disposition') == "inline; filename=user_sheet.pdf"
        assert response.data.startswith(b"%PDF")


@pytest.mark.usefixtures("session")
class TestNewUserDatasheet:
    @contextlib.contextmanager
    def assert_create_confirmed(self, test_client: TestClient):
        with test_client.flashes_message("Benutzer angelegt.", category="success"):
            yield

    def test_user_create_data_sheet(
        self, test_client: TestClient, room: Room, config: Config
    ):
        with self.assert_create_confirmed(test_client):
            test_client.assert_redirects(
                "user.create",
                method="post",
                data={
                    "now": True,
                    "name": "Test User",
                    "building": room.building.id,
                    "level": room.level,
                    "room_number": room.number,
                    "login": "testuser",
                    "mac": "70:de:ad:be:ef:07",
                    "birthdate": "1990-01-01",
                    "email": "",
                    "property_group": config.member_group.id,
                },
            )
        response = test_client.assert_ok("user.user_sheet")
        assert WebStorage.q.count() == 1
        assert response.headers.get('Content-Type') == "application/pdf"
        assert response.headers.get('Content-Disposition') == "inline; filename=user_sheet.pdf"
        assert response.data.startswith(b"%PDF")

    @pytest.fixture(scope="session")
    def mac(self) -> str:
        return "00:de:ad:be:ef:00"

    @pytest.fixture(scope="class")
    def other_user(self, class_session, mac) -> User:
        other_user = UserFactory(with_host=True, host__interface__mac=mac)
        class_session.flush()
        # assert len(other_user.hosts) == 1
        return other_user

    def test_user_host_annexation(
        self, test_client: TestClient, room: Room, other_user: User, mac, config: Config
    ):
        move_in_formdata = {
            "now": True,
            "name": "Test User",
            "building": str(room.building.id),
            "level": str(room.level),
            "room_number": room.number,
            "login": "testuser",
            "mac": mac,
            "email": "",
            "birthdate": "1990-01-01",
            "property_group": config.member_group.id,
        }
        response = test_client.assert_response_code(
            "user.create", method="post", data=move_in_formdata, code=400
        )
        assert response.location is None

        move_in_formdata.update(annex="y")
        with self.assert_create_confirmed(test_client):
            test_client.assert_redirects(
                "user.create", method="post", data=move_in_formdata
            )
