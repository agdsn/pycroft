import pytest
from flask import url_for

from pycroft.model._all import PropertyGroup
from .assertions import TestClient


@pytest.mark.usefixtures("admin_logged_in")
class TestPropertiesFrontend:
    def test_property_gets_added(self, test_client: TestClient):
        group_name = "This is my first property group"
        # first time: a redirect
        response = test_client.assert_response_code(
            "properties.property_group_create",
            code=302,
            method="post",
            data={"name": group_name},
        )
        assert response.location == url_for('properties.property_groups', _external=True)
        response = test_client.assert_url_response_code(response.location, code=200)

        content = response.data.decode('utf-8')
        # This actually should be `assert_flashed`
        assert group_name in content

        assert PropertyGroup.q.filter_by(name=group_name).count() == 1, \
            f"Expected one property group of name '{group_name}'"
