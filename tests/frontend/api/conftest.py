import pytest

from tests.frontend.assertions import TestClient


@pytest.fixture(scope="module", autouse=True)
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.fixture(scope="module", autouse=True)
def api_key(app) -> str:
    api_key = "secrettestapikey"
    app.config["PYCROFT_API_KEY"] = api_key
    return api_key


@pytest.fixture(scope="module", autouse=True)
def max_clients(app) -> int:
    max_clients = 5
    app.config["MAX_MPSKS"] = max_clients
    return max_clients


# TODO put this into the client
@pytest.fixture(scope="module")
def auth_header(api_key) -> dict[str, str]:
    # see `api.v0.parse_authorization_header`
    return {"AUTHORIZATION": f"apikey {api_key}"}
