#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import datetime

import pytest
from sqlalchemy.orm import Session

from pycroft.helpers.interval import single
from pycroft.lib.search import user_search_query
from pycroft.model.user import User, PropertyGroup
from tests.factories import UserFactory, PropertyGroupFactory, \
    MembershipFactory


def s(**kw):
    return user_search_query(**kw).all()


@pytest.fixture(scope="module")
def other_user(module_session: Session) -> User:
    return UserFactory.create(
        name="Franz", login="franz", email="fr@a.nz", with_host=True
    )


@pytest.mark.usefixtures("session")
class TestSearchUserBaseData:
    @pytest.fixture(scope="class", autouse=True)
    def property_group(self, class_session) -> PropertyGroup:
        return PropertyGroupFactory.create()

    @pytest.fixture(scope="class")
    def user(self, class_session) -> User:
        return UserFactory.create(
            with_host=True,
            name='Hans Müller',
            login='hans.mueller',
            email='hans@mueller.com',
        )

    def test_name_search(self, user):
        assert s(name="Hans") == [user]
        assert s(name="Corect, Horse") == []

    def test_login_search(self, user):
        assert s(login="mueller") == [user]
        assert s(login="correcthorsebatterystaple") == []

    def test_email_search(self, user):
        assert s(email="mueller.com") == [user]
        assert s(email="franz.com") == []

    def test_user_id_search(self, user):
        assert s(user_id=user.id) == [user]
        assert s(user_id=1e9) == []

    # one might add tests for person_id, building, mac, query …


class TestUser:
    @pytest.fixture(scope="class", autouse=True)
    def group(self, class_session):
        return PropertyGroupFactory.create()

    @pytest.fixture(scope="class", autouse=True)
    def old_group(self, class_session):
        return PropertyGroupFactory.create()

    @pytest.fixture(scope="class", autouse=True)
    def user(self, class_session, group, old_group):
        user = UserFactory.create(
            with_host=True,
            host__interface__mac="00:de:ad:be:ef:00",
            with_membership=True,
            membership__group=group,
        )
        MembershipFactory.create(
            user=user,
            group=old_group,
            active_during=single(datetime.datetime(2020, 1, 1)),
        )
        return user

    def test_past_property_group_search(self, old_group):
        assert s(property_group_id=old_group.id) == []

    def test_property_group_search(self, group, user):
        assert s(property_group_id=group.id) == [user]
