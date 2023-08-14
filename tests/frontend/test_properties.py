import pytest
from flask import url_for

from pycroft.model._all import PropertyGroup
from .assertions import TestClient


@pytest.fixture(scope="module")
def client(module_test_client: TestClient) -> TestClient:
    return module_test_client


@pytest.mark.usefixtures("admin_logged_in")
class TestPropertiesFrontend:
    def test_property_gets_added(self, client: TestClient):
        group_name = "This is my first property group"
        # first time: a redirect
        response = client.assert_redirects(
            "properties.property_group_create",
            method="post",
            data={"name": group_name},
            expected_location=url_for("properties.property_groups"),
        )
        response = client.assert_url_response_code(response.location, code=200)

        content = response.data.decode('utf-8')
        # This actually should be `assert_flashed`
        assert group_name in content

        assert PropertyGroup.q.filter_by(name=group_name).count() == 1, \
            f"Expected one property group of name '{group_name}'"
