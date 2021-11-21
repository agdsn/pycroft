# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.helpers.interval import IntervalSet, UnboundedInterval, closed
from pycroft.lib.membership import grant_property, deny_property, \
    remove_property, make_member_of, remove_member_of, known_properties
from pycroft.model import session
from pycroft.model.user import Membership, Property
from tests import FactoryDataTestBase
from tests.factories import PropertyGroupFactory, UserFactory


class Test_030_Membership(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.group = PropertyGroupFactory.create()
        self.user, self.processor = UserFactory.create_batch(2)

    def assertMembershipIntervalsEqual(self, expected):
        memberships = session.session.query(Membership).filter_by(
            user=self.user, group=self.group)
        got = IntervalSet(m.active_during.closure for m in memberships)
        assert expected == got, "IntervalSets differ: " \
                                "expected {!r}" \
                                "got      {!r}".format(expected, got)

    def add_membership(self, during):
        make_member_of(self.user, self.group, self.processor, during)
        session.session.commit()

    def remove_membership(self, during=UnboundedInterval):
        remove_member_of(self.user, self.group, self.processor, during)
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


class Test_040_Property(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.property_name = 'granted_property'
        self.group = PropertyGroupFactory(granted={self.property_name},
                                          denied={'denied_property'})

    def test_0010_grant_property(self):
        prop = grant_property(self.group, self.property_name)

        assert Property.get(prop.id) is not None

        db_property = Property.get(prop.id)

        assert db_property.name == self.property_name
        assert db_property.property_group == self.group
        assert db_property.granted
        assert self.group.property_grants[self.property_name]

        session.session.delete(db_property)
        session.session.commit()

    def test_0020_deny_property(self):
        prop = deny_property(self.group, self.property_name)
        assert Property.get(prop.id) is not None

        db_property = Property.get(prop.id)

        assert db_property.name == self.property_name
        assert db_property.property_group == self.group
        assert not db_property.granted
        assert not self.group.property_grants[self.property_name]

        session.session.delete(db_property)
        session.session.commit()

    def test_0030_remove_property(self):
        try:
            remove_property(self.group, self.property_name)
        except ValueError as e:
            self.fail(str(e))

    def test_0035_remove_wrong_property(self):
        self.assertRaises(ValueError, remove_property, self.group,
                          "non_existent_property")


class TestPropertyFetch(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        PropertyGroupFactory.create(granted={'member', 'must_pay', 'network_access'})
        PropertyGroupFactory.create(granted={'violation'}, denied={'network_access'})

    def test_known_properties(self):
        assert known_properties() == {'member', 'must_pay', 'network_access', 'violation'}
