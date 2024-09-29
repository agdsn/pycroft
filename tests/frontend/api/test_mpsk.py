import pytest

from pycroft.lib.mpsk_client import mpsk_client_create
from pycroft.model.user import User

from tests import factories as f


class TestAddMpsk:
    VALID_DATA = {"password": "password", "mac": "00:de:ad:be:ef:00", "name": "Fancy TV"}
    INVALID_PASSWORD = {"password": "p", "mac": "00:de:ad:be:ef:00", "name": "Fancy TV"}
    INVALID_name = {"password": "password", "mac": "00:de:ad:be:ef:00"}

    def test_valid_mpsk_device(self, client, auth_header, url, session, user):
        resp = client.assert_url_ok(url, headers=auth_header, method="POST", data=self.VALID_DATA)
        session.refresh(user)
        assert len(mpsk_clients := user.mpsk_clients) == 1

        assert isinstance(j := resp.json, dict)
        assert j.get("id") == mpsk_clients[0].id

    def test_mpsk_device_same_mac(self, client, auth_header, url, session, user):
        client.assert_url_ok(url, headers=auth_header, method="POST", data=self.VALID_DATA)
        session.refresh(user)
        assert len(user.mpsk_clients) == 1

        client.assert_url_response_code(
            url, code=409, headers=auth_header, method="POST", data=self.VALID_DATA
        )

    # TODO negative test cases
    def test_invalid_password(self, client, auth_header, url, session, user):
        client.assert_url_response_code(
            url, code=401, headers=auth_header, method="POST", data=self.INVALID_PASSWORD
        )
        session.refresh(user)
        assert len(user.mpsk_clients) == 0

    @pytest.mark.parametrize("name", ("", "     ", " ", "   ", "  "))
    def test_invalid_name(self, client, auth_header, url, session, user, name):
        self.INVALID_name["name"] = name
        client.assert_url_response_code(
            url, code=400, headers=auth_header, method="POST", data=self.INVALID_name
        )

    @pytest.mark.parametrize(
        "data",
        (
            {},
            {"password": "password"},
            {"mac": "00:de:ad:be:ef:00"},
            {"name": "Fancy TV"},
            VALID_DATA | {"mac": "badmac"},
        ),
    )
    def test_bad_data(self, client, auth_header, url, data):
        client.assert_url_response_code(
            url, code=422, headers=auth_header, method="POST", data=data
        )

    @pytest.fixture(scope="module")
    def url(self, user) -> str:
        return f"api/v0/user/{user.id}/add-mpsk"

    def test_add_mpsk_needs_wifi_hash(self, client, auth_header, user_without_wifi_pw):
        client.assert_url_response_code(
            f"api/v0/user/{user_without_wifi_pw.id}/add-mpsk",
            # 412 precondition failed
            # The request itself is valid, so 422 (unprocessable entity) is slightly inaccurate
            code=412,
            headers=auth_header,
            method="POST",
            data=self.VALID_DATA,
        )

    @pytest.mark.parametrize(
        "data",
        (
            {
                "password": "password",
                "mac": "00:de:ad:be:ef:0",
                "name": "Fancy TV",
            },
        ),
    )
    def test_max_mpsk_clients(self, client, auth_header, user, session, max_clients, url, data):

        for i in range(max_clients):
            default = data["mac"]
            data["mac"] = f"{data['mac']}{i}"
            client.assert_url_ok(url, headers=auth_header, method="POST", data=data)
            data["mac"] = default
            session.refresh(user)
            assert len(user.mpsk_clients) == i + 1

        data["mac"] = f"{data['mac']}{max_clients}"
        client.assert_url_response_code(
            url, code=400, headers=auth_header, method="POST", data=data
        )


class TestDeleteMpsk:
    VALID_PASSWORD = {"password": "password"}
    INVALID_PASSWORD = {"password": "p"}

    def test_delete_no_mpsk(self, client, auth_header, session, user):
        client.assert_url_response_code(
            f"api/v0/user/{user.id}/delete-mpsk/0",
            code=404,
            headers=auth_header,
            method="POST",
            data=self.VALID_PASSWORD,
        )

    def test_delete_mpsk_unauthed(self, client, auth_header, url, session, user):
        mpsk_client = mpsk_client_create(
            session, owner=user, mac="00:de:ad:be:ef:00", name="Fancy TV", processor=user
        )
        session.flush()
        client.assert_url_response_code(
            url + str(mpsk_client.id),
            code=401,
            headers=auth_header,
            method="POST",
            data=self.INVALID_PASSWORD,
        )

    def test_delete_mpsk(self, client, auth_header, url, session, user):
        mpsk_client = mpsk_client_create(
            session, owner=user, mac="00:de:ad:be:ef:00", name="Fancy TV", processor=user
        )
        session.flush()
        client.assert_url_ok(
            url + str(mpsk_client.id), headers=auth_header, method="POST", data=self.VALID_PASSWORD
        )

    @pytest.fixture(scope="module")
    def url(self, user) -> str:
        return f"api/v0/user/{user.id}/delete-mpsk/"

@pytest.fixture(scope="module")
def user(module_session) -> User:
    return f.UserFactory()


@pytest.fixture
def user_without_wifi_pw(module_session) -> User:
    return f.UserFactory(wifi_passwd_hash=None)


@pytest.fixture
def user_with_encrypted_wifi(module_session) -> User:
    return f.UserFactory(wifi_passwd_hash="{somecryptprefix}garbledpasswordhash")
