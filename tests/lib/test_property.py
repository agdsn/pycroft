# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from tests import FixtureDataTestBase
from tests.lib.fixtures.property_fixtures import UserData, PropertyGroupData,\
    PropertyData, MembershipData, TrafficGroupData

from pycroft.lib.property import (
    create_membership, delete_membership,
    create_property_group, delete_property_group,
    create_traffic_group, delete_traffic_group,
    grant_property, deny_property, remove_property,
    _create_group, _delete_group
)

from pycroft.model.property import TrafficGroup, PropertyGroup, Property,\
    Membership, Group
from pycroft.model.user import User
from pycroft.model import session

from datetime import datetime, timedelta
from sqlalchemy import Column, ForeignKey
from sqlalchemy.types import Integer

class Test_010_PropertyGroup(FixtureDataTestBase):
    datasets = [PropertyGroupData]

    def test_0010_create_property_group(self):
        name = "dummy_property_group2"

        property_group = create_property_group(name=name)

        self.assertIsNotNone(PropertyGroup.q.get(property_group.id))

        db_property_group = PropertyGroup.q.get(property_group.id)

        self.assertEqual(db_property_group.name, name)

        session.session.delete(db_property_group)
        session.session.commit()

    def get_property_group(self):
        return PropertyGroup.q.filter_by(
            name=PropertyGroupData.dummy_property_group1.name).one()

    def test_0020_delete_property_group(self):
        test_property_group = self.get_property_group()
        del_property_group = delete_property_group(test_property_group.id)

        self.assertIsNone(PropertyGroup.q.get(del_property_group.id))

    def test_0025_delete_wrong_property_group(self):
        test_property_group = self.get_property_group()
        self.assertRaises(ValueError, delete_property_group,
                          test_property_group.id + 100)


class Test_020_TrafficGroup(FixtureDataTestBase):
    datasets = [TrafficGroupData]

    def test_0010_create_traffic_group(self):
        name = "dummy_traffic_group2"
        traffic_limit = 100000

        traffic_group = create_traffic_group(name=name,
            traffic_limit=traffic_limit)

        self.assertIsNotNone(TrafficGroup.q.get(traffic_group.id))

        db_traffic_group = TrafficGroup.q.get(traffic_group.id)

        self.assertEqual(db_traffic_group.name, name)
        self.assertEqual(db_traffic_group.traffic_limit, traffic_limit)

        session.session.delete(db_traffic_group)
        session.session.commit()

    def get_traffic_group(self):
        return TrafficGroup.q.filter_by(
            name=TrafficGroupData.dummy_traffic_group1.name).one()

    def test_0020_delete_traffic_group(self):
        test_traffic_group = self.get_traffic_group()
        del_traffic_group = delete_traffic_group(test_traffic_group.id)

        self.assertIsNone(TrafficGroup.q.get(del_traffic_group.id))

    def test_0025_delete_wrong_traffic_group(self):
        test_traffic_group = self.get_traffic_group()
        self.assertRaises(ValueError, delete_traffic_group,
                          test_traffic_group.id + 100)


class Test_030_Membership(FixtureDataTestBase):
    datasets = [MembershipData, PropertyGroupData, UserData]

    def test_0010_create_membership(self):
        start_date = datetime.utcnow()
        end_date = datetime.utcnow() + timedelta(hours=1)
        group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.dummy_property_group1.name).one()
        user = User.q.filter_by(login=UserData.dummy_user1.login).one()

        membership = create_membership(
            start_date=start_date, end_date=end_date,
            group=group, user=user)

        self.assertIsNotNone(Membership.q.get(membership.id))

        db_membership = Membership.q.get(membership.id)

        self.assertEqual(db_membership.start_date, start_date)
        self.assertEqual(db_membership.end_date, end_date)
        self.assertEqual(db_membership.group, group)
        self.assertEqual(db_membership.user, user)

        session.session.delete(db_membership)
        session.session.commit()

    def test_0020_delete_membership(self):
        test_membership = Membership.q.first()
        del_membership = delete_membership(test_membership.id)

        self.assertIsNone(Membership.q.get(del_membership.id))

    def test_0025_delete_wrong_membership(self):
        test_membership = Membership.q.first()
        self.assertRaises(ValueError, delete_membership,
            test_membership.id + 100)


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

        self.assertRaises(ValueError, remove_property,
                          self.group, self.property_name + "_fail")
        self.assertRaises(ValueError, remove_property,
                          empty_group,
                          self.property_name)


class Test_050_MalformedGroup(FixtureDataTestBase):
    datasets = [UserData]

    class MalformedGroup(Group):
        id = Column(Integer, ForeignKey("group.id"), primary_key=True)
        __mapper_args__ = {'polymorphic_identity': 'malformed_group'}

    def test_0010_create_malformed_group(self):
        name = "malformed_group1"

        self.assertRaises(ValueError, _create_group,
            group_type='malformed_group',
            name=name, id=100)

    def test_0020_delete_malformed_group(self):
        malformed_group = Test_050_MalformedGroup.MalformedGroup(id=1000,
            name="malformed_group2")

        session.session.add(malformed_group)
        session.session.commit()

        self.assertRaises(ValueError, _delete_group, malformed_group.id)

        session.session.delete(malformed_group)
        session.session.commit()

