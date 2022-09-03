#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest

from ldap_sync.sources.db import fetch_users_to_sync, UserProxyType
from tests import factories


@pytest.fixture(scope='module')
def group(module_session):
    return factories.PropertyGroupFactory.create(granted={'ldap', 'ldap_login_enabled'})


@pytest.fixture(scope='module')
def deny_group(module_session):
    return factories.PropertyGroupFactory.create(denied={'ldap_login_enabled'})


@pytest.fixture
def deny_membership(session, deny_group, user):
    return factories.MembershipFactory(
        user=user, group=deny_group, includes_today=True,
    )

@pytest.fixture(scope='module')
def user(module_session, group):
    return factories.UserFactory.create(
        with_unix_account=True,
        with_membership=True,
        membership__group=group,
    )


def test_one_user_fetch(session, user):
    assert fetch_users_to_sync(session) == [
        tuple(UserProxyType(user, should_be_blocked=False))
    ]


def test_one_user_fetch_with_property(session, user):
    assert fetch_users_to_sync(session, required_property="nonexistent") == []


def test_one_user_fetch_with_existent_property(session, user):
    assert fetch_users_to_sync(session, required_property='ldap') == [
        tuple(UserProxyType(user, should_be_blocked=False))
    ]


def test_one_user_fetch_with_blockage(session, user, deny_membership):
    assert fetch_users_to_sync(session, required_property='ldap') == [
        tuple(UserProxyType(user, should_be_blocked=True))
    ]
