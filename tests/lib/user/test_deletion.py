#  Copyright (c) 2021. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from datetime import datetime, date
from typing import Sequence

import pytest

from pycroft.helpers.interval import closed, closedopen
from pycroft.helpers.utc import with_min_time
from pycroft.lib.user_deletion import (
    get_archivable_members,
    archive_users,
    ArchivableMemberInfo,
)
from pycroft.model.user import User
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


def filter_members(members, user):
    return [(u, id, end) for u, id, end in members if u == user]


def assert_member_present(
    members: Sequence[ArchivableMemberInfo],
    expected_user: User,
    expected_end_date: date,
):
    relevant_members = filter_members(members, expected_user)
    assert len(relevant_members) == 1
    [(_, mem_id, mem_end)] = relevant_members
    assert mem_id is not None
    assert mem_end.date() == expected_end_date


def assert_member_absent(
    members: Sequence[ArchivableMemberInfo],
    expected_absent_user: User,
):
    assert not filter_members(members, expected_absent_user)


class TestArchivableUserSelection:
    @pytest.fixture(
        scope="class",
        params=[date(2020, 3, 1), date(2020, 1, 1), date(2020, 12, 15)],
    )
    def end_date(self, request):
        return request.param

    @pytest.fixture(scope='class')
    def do_not_archive_group(self, class_session):
        return PropertyGroupFactory(granted={'do-not-archive'})

    @pytest.fixture(scope="class")
    def old_user(self, class_session, config, do_not_archive_group, end_date) -> User:
        user = UserFactory.create(
            registered_at=datetime(2000, 1, 1),
            with_membership=True,
            membership__active_during=closed(
                with_min_time(date(2020, 1, 1)), with_min_time(end_date)
            ),
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

    @pytest.mark.parametrize("year", [2022, 2023, 2024])
    def test_old_users_in_deletion_list_after(self, session, old_user, year, end_date):
        members = get_archivable_members(session, current_year=year)
        assert_member_present(members, old_user, end_date)

    @pytest.mark.parametrize("year", [2019, 2020, 2021])
    def test_old_user_not_in_list_before(self, session, old_user, year):
        assert_member_absent(
            get_archivable_members(session, current_year=year), old_user
        )

    @pytest.mark.parametrize("year", list(range(2018, 2023)))
    def test_user_with_do_not_archive_not_in_list(
        self, session, old_user, do_not_archive_membership, year
    ):
        assert_member_absent(
            get_archivable_members(session, current_year=year), old_user
        )

    @pytest.mark.parametrize('num_hosts', [0, 2])
    def test_user_with_host_in_list(self, session, old_user, num_hosts, end_date):
        if num_hosts:
            HostFactory.create_batch(num_hosts, owner=old_user)
        members = get_archivable_members(session)
        assert_member_present(members, old_user, end_date)

    def test_user_with_room_in_list(self, session, old_user, end_date):
        with session.begin_nested():
            old_user.room = None
            session.add(old_user)
        members = get_archivable_members(session)
        assert_member_present(members, old_user, end_date)


class TestUserArchival:
    @pytest.fixture(scope='class')
    def archivable_users(self, class_session, config):
        return UserFactory.create_batch(
            3,
            with_membership=True,
            membership__active_during=closed(datetime(2020, 1, 1), datetime(2020, 3, 1)),
            membership__group=config.member_group,
            with_host=True, patched=True,
            with_creation_log_entry=True,
            with_random_task=True,
        )

    @pytest.fixture(scope='class')
    def archived_users(self, class_session, archivable_users):
        archive_users(class_session, [u.id for u in archivable_users])
        return archivable_users

    @pytest.mark.parametrize('index', [0, 1, 2])
    def test_user_archival(self, archived_users, index):
        user = archived_users[index]
        assert user.tasks == [], "archival did not delete tasks"
        assert [le for le in user.log_entries
                if le.created_at == user.registered_at] == [], "archival did not delete logs"
        assert user.hosts == [], "archival did not delete hosts"
        assert 'archived' in user.current_properties
