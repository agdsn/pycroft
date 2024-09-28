import pytest
from pycroft.model.user import User

from tests import factories as f
from tests.frontend.assertions import TestClient


def test_api_get(client, auth_header, session, user):
    resp = client.assert_url_ok(
        f"api/v0/user/{user.id}/add-mpsk",
        headers=auth_header,
        method="POST",
        data={"password": "password", "mac": "00:de:ad:be:ef:00", "name": "Fancy TV"},
    )
    # TODO negative test cases, check for adequate response (id)
    session.refresh(user)
    assert len(mpsk_clients := user.mpsk_clients) == 1

    assert (j := resp.json)
    assert j.get("id") == mpsk_clients[0].id


def test_add_mpsk_needs_wifi_hash(client, auth_header, user_without_wifi_pw):
    # TODO what kind of response do we expect?
    _ = client.assert_url_response_code(
        f"api/v0/user/{user_without_wifi_pw.id}/add-mpsk",
        400,
        headers=auth_header,
        method="POST",
        data={"password": "password", "mac": "00:de:ad:be:ef:00", "name": "Fancy TV"},
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


@pytest.fixture(scope="module", autouse=True)
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.fixture(scope="module", autouse=True)
def api_key(app) -> str:
    api_key = "secrettestapikey"
    app.config["PYCROFT_API_KEY"] = api_key
    return api_key


# TODO put this into the client
@pytest.fixture(scope="module")
def auth_header(api_key) -> dict[str, str]:
    # see `api.v0.parse_authorization_header`
    return {"AUTHORIZATION": f"apikey {api_key}"}
