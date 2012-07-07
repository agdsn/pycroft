# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet, SQLAlchemyFixture, DataTestCase
from fixture.style import TrimmedNameStyle
import unittest
from datetime import datetime, timedelta

from pycroft.model import session, user, properties, _all
from pycroft import model

class DormitoryData(DataSet):
    class dummy_house:
        number = "01"
        short_name = "abc"
        street = "dummy"


class RoomData(DataSet):
    class dummy_room:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house


class UserData(DataSet):
    class dummy_user:
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room

class PropertyGroupData(DataSet):
    class group1:
        name = "group1"
    class group2:
        name = "group2"


class PropertyData(DataSet):
    class prop_test1:
        name = "test1"
        property_group = PropertyGroupData.group1
    class prop_test1_1(prop_test1):
        property_group = PropertyGroupData.group2
    class prop_test2:
        name = "test2"
        property_group = PropertyGroupData.group2


def make_fixture():
    fixture = SQLAlchemyFixture(
            env=_all,
            style=TrimmedNameStyle(suffix="Data"),
            session=session.session,
            scoped_session=session.session._scoped_session,
            engine=session.session.get_engine() )
    return fixture

class Test_010_PropertyResolving(DataTestCase, unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()
        cls.fixture = make_fixture()
        cls.datasets = [DormitoryData, RoomData, UserData, PropertyGroupData, PropertyData]


    def setUp(self):
        super(Test_010_PropertyResolving, self).setUp()
        self.user = user.User.q.get(1)


    def test_0010_assert_correct_fixture(self):
        self.assertEqual(properties.Membership.q.count(), 0)

        self.assertFalse(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        self.assertTrue(properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one().has_property(PropertyData.prop_test1.name))
        self.assertTrue(properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one().has_property(PropertyData.prop_test1.name))
        self.assertTrue(properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one().has_property(PropertyData.prop_test2.name))

    def test_0020_add_membership(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        membership = properties.Membership(start_date=datetime.now(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()

        membership = properties.Membership(start_date=datetime.now(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertTrue(self.user.has_property(PropertyData.prop_test2.name))


    def test_0030_add_timed_membership(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        membership = properties.Membership(start_date=datetime.now(), user=self.user, group=group)
        membership.end_date = membership.start_date + timedelta(days=3)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()

        membership = properties.Membership(user=self.user, group=group)
        membership.start_date = datetime.now() - timedelta(days=3)
        membership.end_date = membership.start_date + timedelta(hours=1)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))


    def test_0040_disable_membership(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        membership = properties.Membership(start_date=datetime.now(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        membership.disable()
        self.assertFalse(self.user.has_property(PropertyData.prop_test1.name))

        membership = properties.Membership(start_date=datetime.now(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()
        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))

        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()
        membership = properties.Membership(start_date=datetime.now(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertTrue(self.user.has_property(PropertyData.prop_test2.name))

        membership.disable()
        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))
