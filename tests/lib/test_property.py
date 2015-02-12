# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.helpers.interval import IntervalSet ,UnboundedInterval, closed
from pycroft.lib.property import (
    grant_property, deny_property, remove_property,
    make_member_of, remove_member_of)
from pycroft.model.property import PropertyGroup, Property, Membership
from pycroft.model.user import User
from pycroft.model import session
from tests import FixtureDataTestBase
from tests.fixtures.dummy.property import PropertyGroupData, PropertyData
from tests.fixtures.dummy.user import UserData


class Test_030_Membership(FixtureDataTestBase):
    datasets = [PropertyGroupData, UserData]

    def setUp(self):
        super(Test_030_Membership, self).setUp()
        self.group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.dummy.name).one()
        self.user = User.q.filter_by(login=UserData.dummy.login).one()

    def assertMembershipIntervalsEqual(self, expected):
        memberships = session.session.query(Membership).filter_by(
            user=self.user, group=self.group)
        got = IntervalSet(closed(m.begins_at, m.ends_at) for m in memberships)
        assert expected == got, "IntervalSets differ: " \
                                "expected {0!r}" \
                                "got      {1!r}".format(expected, got)

    def add_membership(self, during):
        make_member_of(self.user, self.group, during)
        session.session.commit()

    def remove_membership(self, during=UnboundedInterval):
        remove_member_of(self.user, self.group, during)
        session.session.commit()

    def test_adding_single_membership(self):
        begins_at = session.utcnow()
        ends_at = begins_at + timedelta(hours=1)
        during = closed(begins_at, ends_at)

        self.add_membership(during)
        self.assertMembershipIntervalsEqual(IntervalSet(during))

    def test_join_overlapping_memberships(self):
        begins_at1 = session.utcnow()
        ends_at1 = begins_at1 + timedelta(hours=2)
        during1 = closed(begins_at1, ends_at1)
        begins_at2 = begins_at1 + timedelta(hours=1)
        ends_at2 = begins_at1 + timedelta(hours=3)
        during2 = closed(begins_at2, ends_at2)

        self.add_membership(during1)
        self.add_membership(during2)
        self.assertMembershipIntervalsEqual(IntervalSet(closed(begins_at1, ends_at2)))

    def test_removing_all_memberships(self):
        begins_at1 = session.utcnow()
        ends_at1 = begins_at1 + timedelta(hours=1)
        during1 = closed(begins_at1, ends_at1)
        begins_at2 = begins_at1 + timedelta(hours=2)
        ends_at2 = begins_at1 + timedelta(hours=3)
        during2 = closed(begins_at2, ends_at2)

        self.add_membership(during1)
        self.add_membership(during2)
        self.remove_membership()
        self.assertMembershipIntervalsEqual(IntervalSet())

    def test_removing_memberships(self):
        t0 = session.utcnow()
        t1 = t0 + timedelta(hours=1)
        t2 = t0 + timedelta(hours=2)
        t3 = t0 + timedelta(hours=3)
        t4 = t0 + timedelta(hours=4)
        t5 = t0 + timedelta(hours=5)
        self.add_membership(closed(t0, t2))
        self.add_membership(closed(t3, t5))
        self.remove_membership(closed(t1, t4))
        self.assertMembershipIntervalsEqual(IntervalSet(
            (closed(t0, t1), closed(t4, t5))))


class Test_040_Property(FixtureDataTestBase):
    datasets = [PropertyGroupData, PropertyData]

    def setUp(self):
        super(Test_040_Property, self).setUp()
        self.test_property = Property.q.filter_by(
            name=PropertyData.granted.name).one()
        self.property_name = self.test_property.name
        self.group = self.test_property.property_group

    def test_0010_grant_property(self):
        prop = grant_property(self.group, self.property_name)

        self.assertIsNotNone(Property.q.get(prop.id))

        db_property = Property.q.get(prop.id)

        self.assertEqual(db_property.name, self.property_name)
        self.assertEqual(db_property.property_group, self.group)
        self.assertTrue(db_property.granted)
        self.assertTrue(self.group.property_grants[self.property_name])

        session.session.delete(db_property)
        session.session.commit()

    def test_0020_deny_property(self):
        prop = deny_property(self.group, self.property_name)
        self.assertIsNotNone(Property.q.get(prop.id))

        db_property = Property.q.get(prop.id)

        self.assertEqual(db_property.name, self.property_name)
        self.assertEqual(db_property.property_group, self.group)
        self.assertFalse(db_property.granted)
        self.assertFalse(self.group.property_grants[self.property_name])

        session.session.delete(db_property)
        session.session.commit()

    def test_0030_remove_property(self):
        try:
            remove_property(self.group, self.property_name)
        except ValueError as e:
            self.fail(e.message)

    def test_0035_remove_wrong_property(self):
        self.assertRaisesInTransaction(ValueError, remove_property, self.group,
                                       "non_existent_property")
