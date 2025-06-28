#  Copyright (c) 2025. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from datetime import datetime

import pytest

from factory import SubFactory

from pycroft.model.user import User
from tests import factories as f
from tests.factories import ActiveMemberPropertyGroupFactory


class TestActive:
    @pytest.fixture(scope="module")
    def url(self, user) -> str:
        return "api/v0/user/active"

    def test_without_data(self, client, url, auth_header):
        response = client.assert_url_ok(
            url,
            headers=auth_header,
            method="POST",
            data={"uid": 12, "name": "user.name", "fname": "", "byear": 2020},
        )
        assert response.status_code == 200
        assert response.json == {"response": False}

    def test_with_data(self, client, url, auth_header, user):
        response = client.assert_url_ok(
            url,
            headers=auth_header,
            method="POST",
            data={"uid": user.id, "name": user.name, "fname": "", "byear": datetime.now().year},
        )
        assert response.status_code == 200

        assert response.json == {"response": True}

    def test_without_birthday(self, client, url, auth_header, user):
        response = client.assert_url_ok(
            url,
            headers=auth_header,
            method="POST",
            data={"uid": user.id, "name": user.name, "fname": ""},
        )
        assert response.status_code == 200

        assert response.json == {"response": True}

    def test_non_active(self, client, url, auth_header, member):
        response = client.assert_url_ok(
            url,
            headers=auth_header,
            method="POST",
            data={"uid": member.id, "name": member.name, "fname": "", "byear": 2020},
        )
        assert response.status_code == 200
        assert response.json == {"response": False}


@pytest.fixture(scope="module")
def user(module_session, config) -> User:
    user = f.UserFactory(
        birthdate=datetime.now(),
        with_membership=True,
        membership__group=SubFactory(ActiveMemberPropertyGroupFactory),
        membership__includes_today=True,
    )
    module_session.flush()
    return user


@pytest.fixture(scope="module")
def member(module_session, config) -> User:
    return f.UserFactory(
        with_membership=True,
        membership__group=SubFactory(ActiveMemberPropertyGroupFactory),
        membership__includes_today=True,
    )
