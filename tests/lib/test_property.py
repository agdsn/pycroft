# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.lib.property import (
    create_membership, grant_property, deny_property, remove_property)
from pycroft.model.property import PropertyGroup, Property, Membership
from pycroft.model.user import User
from pycroft.model import session
from tests import FixtureDataTestBase
from tests.lib.fixtures.property_fixtures import (
    UserData, PropertyGroupData, PropertyData, MembershipData)


class Test_030_Membership(FixtureDataTestBase):
    datasets = [MembershipData, PropertyGroupData, UserData]

    def test_0010_create_membership(self):
        start_date = session.utcnow()
        end_date = start_date + timedelta(hours=1)
        group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.dummy_property_group1.name).one()
        user = User.q.filter_by(login=UserData.dummy_user1.login).one()

        membership = create_membership(
            start_date=start_date, end_date=end_date,
            group=group, user=user)

        self.assertIsNotNone(Membership.q.get(membership.id))

        self.assertEqual(membership.start_date, start_date)
        self.assertEqual(membership.end_date, end_date)
        self.assertEqual(membership.group, group)
        self.assertEqual(membership.user, user)

        session.session.delete(membership)
        session.session.commit()


class Test_040_Property(FixtureDataTestBase):
    datasets = [PropertyGroupData, PropertyData]

    def setUp(self):
        super(Test_040_Property, self).setUp()
        self.test_property = Property.q.filter_by(
            name=PropertyData.dummy_property1.name).one()
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
        empty_group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.dummy_property_group2_empty.name).one()

        self.assertRaisesInTransaction(ValueError, remove_property, self.group,
                                       self.property_name + "_fail")
        self.assertRaisesInTransaction(ValueError, remove_property, empty_group,
                                       self.property_name)
