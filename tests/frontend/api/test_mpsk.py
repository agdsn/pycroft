import pytest
from pycroft.model.user import User

from tests import factories as f


class TestAddMpsk:
    VALID_DATA = {"password": "password", "mac": "00:de:ad:be:ef:00", "name": "Fancy TV"}

    def test_valid_mpsk_device(self, client, auth_header, url, session, user):
        resp = client.assert_url_ok(url, headers=auth_header, method="POST", data=self.VALID_DATA)
        session.refresh(user)
        assert len(mpsk_clients := user.mpsk_clients) == 1

        assert isinstance(j := resp.json, dict)
        assert j.get("id") == mpsk_clients[0].id

    # TODO negative test cases

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


@pytest.fixture(scope="module")
def user(module_session) -> User:
    return f.UserFactory()


@pytest.fixture
def user_without_wifi_pw(module_session) -> User:
    return f.UserFactory(wifi_passwd_hash=None)


@pytest.fixture
def user_with_encrypted_wifi(module_session) -> User:
    return f.UserFactory(wifi_passwd_hash="{somecryptprefix}garbledpasswordhash")
