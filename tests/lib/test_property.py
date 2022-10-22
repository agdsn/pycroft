# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import dataclasses
from datetime import timedelta

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from pycroft.helpers.interval import IntervalSet, UnboundedInterval, closed
from pycroft.lib.membership import grant_property, deny_property, \
    remove_property, make_member_of, remove_member_of, known_properties
from pycroft.model.user import Membership, PropertyGroup, User
from tests.factories import PropertyGroupFactory, UserFactory


@dataclasses.dataclass
class MembershipFixture:
    session: Session
    user: User
    group: PropertyGroup
    processor: User

    def add_membership(self, during):
        make_member_of(self.user, self.group, self.processor, during)

    def remove_membership(self, during=UnboundedInterval):
        remove_member_of(self.user, self.group, self.processor, during)

    def assert_membership_intervals(self, expected):
        memberships = self.session.scalars(
            select(Membership).filter_by(user=self.user, group=self.group)
        )
        got = IntervalSet(m.active_during.closure for m in memberships)
        assert expected == got


@pytest.mark.usefixtures("session")
class TestMembership:
    @pytest.fixture(scope="class")
    def group(self, class_session: Session) -> PropertyGroup:
        return PropertyGroupFactory.create()

    @pytest.fixture(scope="class")
    def user(self, class_session: Session) -> User:
        return UserFactory.create()

    @pytest.fixture(name="mf")
    def membership_fixture(self, session, user, group, processor) -> MembershipFixture:
        return MembershipFixture(session, user, group, processor)

    def test_adding_single_membership(self, mf, utcnow):
        begins_at = utcnow
        ends_at = begins_at + timedelta(hours=1)
        during = closed(begins_at, ends_at)

        mf.add_membership(during)
        mf.assert_membership_intervals(IntervalSet(during))

    def test_join_overlapping_memberships(self, mf, utcnow):
        begins_at1 = utcnow
        ends_at1 = begins_at1 + timedelta(hours=2)
        during1 = closed(begins_at1, ends_at1)
        begins_at2 = begins_at1 + timedelta(hours=1)
        ends_at2 = begins_at1 + timedelta(hours=3)
        during2 = closed(begins_at2, ends_at2)

        mf.add_membership(during1)
        mf.add_membership(during2)
        mf.assert_membership_intervals(IntervalSet(closed(begins_at1, ends_at2)))

    def test_removing_all_memberships(self, mf, utcnow):
        begins_at1 = utcnow
        ends_at1 = begins_at1 + timedelta(hours=1)
        during1 = closed(begins_at1, ends_at1)
        begins_at2 = begins_at1 + timedelta(hours=2)
        ends_at2 = begins_at1 + timedelta(hours=3)
        during2 = closed(begins_at2, ends_at2)

        mf.add_membership(during1)
        mf.add_membership(during2)
        mf.remove_membership()
        mf.assert_membership_intervals(IntervalSet())

    def test_removing_memberships(self, mf, utcnow):
        t0 = utcnow
        t1 = t0 + timedelta(hours=1)
        t2 = t0 + timedelta(hours=2)
        t3 = t0 + timedelta(hours=3)
        t4 = t0 + timedelta(hours=4)
        t5 = t0 + timedelta(hours=5)
        mf.add_membership(closed(t0, t2))
        mf.add_membership(closed(t3, t5))
        mf.remove_membership(closed(t1, t4))
        mf.assert_membership_intervals(IntervalSet((closed(t0, t1), closed(t4, t5))))


@pytest.mark.usefixtures("session")
class TestProperty:
    @pytest.fixture(scope="class")
    def property_name(self):
        return "granted_property"

    @pytest.fixture(scope="class")
    def group(self, property_name: str, class_session: Session) -> PropertyGroup:
        return PropertyGroupFactory(granted={property_name}, denied={'denied_property'})

    def test_grant_property(self, group, property_name):
        prop = grant_property(group, property_name)
        assert inspect(prop).persistent
        assert prop.name == property_name
        assert prop.property_group == group
        assert prop.granted
        assert group.property_grants[property_name]

    def test_deny_property(self, group, property_name):
        prop = deny_property(group, property_name)
        assert inspect(prop).persistent
        assert prop.name == property_name
        assert prop.property_group == group
        assert not prop.granted
        assert not group.property_grants[property_name]

    def test_remove_property(self, group, property_name):
        try:
            remove_property(group, property_name)
        except ValueError as e:
            pytest.fail(str(e))

    def test_remove_wrong_property(self, group, property_name):
        with pytest.raises(ValueError):
            remove_property(group, "non_existent_property")


@pytest.fixture
def property_groups(session: Session):
    return [
        PropertyGroupFactory.create(granted={'member', 'must_pay', 'network_access'}),
        PropertyGroupFactory.create(granted={'violation'}, denied={'network_access'}),
    ]


@pytest.mark.usefixtures("property_groups")
def test_known_properties():
    assert known_properties() == {'member', 'must_pay', 'network_access', 'violation'}
