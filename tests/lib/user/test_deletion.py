#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from datetime import datetime, date

import pytest

from pycroft.helpers.interval import closed, closedopen
from pycroft.lib.user_deletion import get_archivable_members
from tests.factories import UserFactory, ConfigFactory, MembershipFactory, \
    PropertyGroupFactory, \
    HostFactory


@pytest.fixture(scope='module')
def config(module_session):
    return ConfigFactory()


def test_no_archivable_users(session):
    assert get_archivable_members(session) == []


def test_users_without_membership_not_in_list(session):
    UserFactory.create_batch(5)
    assert get_archivable_members(session) == []


def assert_archivable_members(members, expected_user, expected_end_date):
    match members:
        case [(user, mem_id, mem_end)]:
            assert user == expected_user
            assert mem_id is not None
            assert mem_end.date() == expected_end_date
        case _:
            pytest.fail()


class TestUserDeletion:
    @pytest.fixture(scope='class')
    def do_not_archive_group(self, class_session):
        return PropertyGroupFactory(granted={'do-not-archive'})

    @pytest.fixture(scope='class')
    def old_user(self, class_session, config, do_not_archive_group):
        user = UserFactory.create(
            registered_at=datetime(2000, 1, 1),
            with_membership=True,
            membership__active_during=closed(datetime(2020, 1, 1), datetime(2020, 3, 1)),
            membership__group=config.member_group,
        )
        MembershipFactory.create(
            user=user, group=do_not_archive_group,
            active_during=closed(datetime(2000, 1, 1), datetime(2010, 1, 1))
        )
        return user

    @pytest.fixture(scope='class', autouse=True)
    def other_users(self, class_session):
        return UserFactory.create_batch(5)

    @pytest.fixture
    def do_not_archive_membership(self, session, old_user, do_not_archive_group):
        return MembershipFactory(
            user=old_user, group=do_not_archive_group,
            active_during=closedopen(datetime(2020, 1, 1), None),
        )

    def test_old_users_in_deletion_list(self, session, old_user):
        members = get_archivable_members(session)
        assert_archivable_members(members, old_user, date(2020, 3, 1))

    def test_old_user_not_in_list_with_long_delta(self, session, old_user):
        delta = date.today() - date(2020, 1, 1)  # before 2020-03-01
        assert get_archivable_members(session, delta) == []

    def test_user_with_do_not_archive_not_in_list(self, session, old_user,
                                                  do_not_archive_membership):
        assert get_archivable_members(session) == []

    @pytest.mark.parametrize('num_hosts', [0, 2])
    def test_user_with_host_in_list(self, session, old_user, num_hosts):
        if num_hosts:
            HostFactory.create_batch(num_hosts, owner=old_user)
        members = get_archivable_members(session)
        assert_archivable_members(members, old_user, date(2020, 3, 1))

    def test_user_with_room_in_list(self, session, old_user):
        with session.begin_nested():
            old_user.room = None
            session.add(old_user)
        members = get_archivable_members(session)
        assert_archivable_members(members, old_user, date(2020, 3, 1))
