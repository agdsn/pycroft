#  Copyright (c) 2025. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest

from pycroft.model.user import User

from tests import factories as f


class TestAPIUser:
    @pytest.fixture(scope="module")
    def url(self, user) -> str:
        return f"api/v0/user/{user.id}"

    def test_user(self, client, url, auth_header):
        response = client.assert_url_ok(url, headers=auth_header, method="GET")
        assert response.status_code == 200


@pytest.fixture(scope="module")
def user(module_session) -> User:
    return f.UserFactory()
