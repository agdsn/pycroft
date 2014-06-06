# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, timedelta
import unittest
from tests import FixtureDataTestBase
from pycroft.model import session, user, property, _all
from tests.model.fixtures.property_fixtures import DormitoryData, RoomData, \
    UserData, PropertyData, PropertyGroupData, TrafficGroupData


class PropertyDataTestBase(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, PropertyGroupData,
                TrafficGroupData, PropertyData]

    def setUp(self):
        super(PropertyDataTestBase, self).setUp()
        self.user = user.User.q.get(1)

    def tearDown(self):
        property.Membership.q.delete()
        session.session.commit()
        super(PropertyDataTestBase, self).tearDown()


class Test_010_PropertyResolving(PropertyDataTestBase):
    def test_0010_assert_correct_fixture(self):
        """simply test that fixtures work
        """
        self.assertEqual(property.Membership.q.count(), 0)

        self.assertFalse(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        self.assertTrue(property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one().has_property(PropertyData.prop_test1.name))
        self.assertTrue(property.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one().has_property(PropertyData.prop_test1.name))
        self.assertTrue(property.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one().has_property(PropertyData.prop_test2.name))

    def test_0020_add_membership(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        membership = property.Membership(start_date=datetime.utcnow(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        # add membership to group2
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()

        membership = property.Membership(start_date=datetime.utcnow(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertTrue(self.user.has_property(PropertyData.prop_test2.name))


    def test_0030_add_timed_membership(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        membership = property.Membership(start_date=datetime.utcnow(), user=self.user, group=group)
        membership.end_date = membership.start_date + timedelta(days=3)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()

        # add expired membership to group2
        membership = property.Membership(user=self.user, group=group)
        membership.start_date = datetime.utcnow() - timedelta(days=3)
        membership.end_date = membership.start_date + timedelta(hours=1)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))


    def test_0040_disable_membership(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        membership = property.Membership(start_date=datetime.utcnow(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        membership.disable()
        session.session.commit()
        self.assertNotIn(group,self.user.active_property_groups)
        self.assertFalse(self.user.has_property(PropertyData.prop_test1.name))

        # add membership to group1
        membership = property.Membership(start_date=datetime.utcnow(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))

        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()

        # add membership to group2
        membership = property.Membership(start_date=datetime.utcnow(), user=self.user, group=group)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertTrue(self.user.has_property(PropertyData.prop_test2.name))

        # disables membership in group2
        membership.disable()
        session.session.commit()
        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))


class Test_020_MembershipValidators(PropertyDataTestBase):
    def test_0010_start_date_default(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()

        p = property.Membership.q.first()
        self.assertIsNotNone(p)
        self.assertIsNotNone(p.start_date)
        self.assertIsNone(p.end_date)

    def test_0020_end_date_before_start(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        p1 = property.Membership(user=self.user, group=group)
        p1.start_date = datetime.utcnow()

        def set_old_date():
            """ Set end_date before start_date
            """
            p1.end_date = datetime.utcnow() - timedelta(hours=2)

        self.assertRaisesRegexp(AssertionError, "you set end date before start date!", set_old_date)

    def test_0030_start_date_after_end(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        p1 = property.Membership(user=self.user, group=group)
        p1.end_date = p1.start_date
        self.assertEqual(p1.end_date, p1.start_date)

        def set_new_start():
            """ Set start_date after end_date
            """
            p1.start_date = datetime.utcnow() + timedelta(hours=2)

        self.assertRaisesRegexp(AssertionError, "you set start date behind end date!", set_new_start)

    def test_0040_set_correct_dates(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        p1 = property.Membership(user=self.user, group=group)
        p1.start_date = datetime.utcnow()
        p1.end_date = datetime.utcnow()

        session.session.add(p1)
        session.session.commit()

        p1.start_date = datetime.utcnow() - timedelta(days=3)
        p1.end_date = datetime.utcnow() + timedelta(days=3)

        session.session.commit()

    def test_0050_clear_end_date(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()

        # add membership to group1
        p1 = property.Membership(user=self.user, group=group)
        p1.start_date = datetime.utcnow()
        p1.end_date = datetime.utcnow()
        session.session.add(p1)
        session.session.commit()

        # test if membership in database
        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertIsNotNone(p1.end_date)

        # clear end_date
        p1.end_date = None
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertIsNone(p1.end_date)


class Test_030_View_Only_Shortcut_Properties(PropertyDataTestBase):
    def test_0010_group_users(self):
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        self.assertEqual(len(group.users), 0)
        self.assertEqual(len(group.active_users), 0)

        # add membership to group1
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()

        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        self.assertEqual(len(group.users), 1)
        self.assertEqual(len(group.active_users), 1)

        p1.disable()
        session.session.commit()
        self.assertEqual(len(group.users), 1)
        self.assertEqual(len(group.active_users), 0)

    def test_0020_user_traffic_groups(self):
        # first have no traffic group
        group = property.TrafficGroup.q.filter_by(name=TrafficGroupData.group1.name).one()
        self.assertEqual(len(self.user.traffic_groups), 0)
        self.assertEqual(len(self.user.active_traffic_groups), 0)

        # add one active traffic group
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        f = property.Membership.q.first()
        self.assertTrue(f.active)
        self.assertEqual(len(self.user.traffic_groups), 1)
        self.assertEqual(len(self.user.active_traffic_groups), 1)

        # adding a property group should not affect the traffic_groups
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 1)
        self.assertEqual(len(self.user.active_traffic_groups), 1)

        # add a second active traffic group - count should be 2
        group = property.TrafficGroup.q.filter_by(name=TrafficGroupData.group2.name).one()
        p2 = property.Membership(user=self.user, group=group)
        session.session.add(p2)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups), 2)

        # disable the second group. active should be one, all 2
        p2.disable()
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups), 1)

        # test a join
        res = session.session.query(user.User, property.TrafficGroup.id).join(user.User.active_traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 1)
        res = session.session.query(user.User, property.TrafficGroup.id).join(user.User.traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)

        # reenable it - but with a deadline - both counts should be 2
        p2.end_date = datetime.utcnow() + timedelta(days=1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups), 2)

        # Add a second membership to the first group - should not affect the count
        group = property.Group.q.filter_by(name=TrafficGroupData.group1.name).one()
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups), 2)

        # disabling the new one should also not affect.
        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups), 2)

        # test a join
        res = session.session.query(user.User, property.TrafficGroup.id).join(user.User.active_traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)
        res = session.session.query(user.User, property.TrafficGroup.id).join(user.User.traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)

    def test_0030_user_property_groups(self):
        # first have no property group
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        self.assertEqual(len(self.user.property_groups), 0)
        self.assertEqual(len(self.user.active_property_groups), 0)

        # add one active property group
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        f = property.Membership.q.first()
        self.assertTrue(f.active)
        self.assertEqual(len(self.user.property_groups), 1)
        self.assertEqual(len(self.user.active_property_groups), 1)

        # adding a traffic group should not affect the property_group
        group = property.TrafficGroup.q.filter_by(name=TrafficGroupData.group2.name).one()
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 1)
        self.assertEqual(len(self.user.active_property_groups), 1)

        # add a second active property group - count should be 2
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups), 2)

        # disable the second group. active should be one, all 2
        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups), 1)

        # test a join
        res = session.session.query(user.User, property.PropertyGroup.id).join(user.User.active_property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 1)
        res = session.session.query(user.User, property.PropertyGroup.id).join(user.User.property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)

        # reenable it - but with a deadline - both counts should be 2
        p1.end_date = datetime.utcnow() + timedelta(days=1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups), 2)

        # Add a second membership to the first group - should not affect the count
        group = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups), 2)

        # disabling the new one should also not affect.
        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups), 2)

        # test a join
        res = session.session.query(user.User, property.PropertyGroup).join(user.User.active_property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)
        res = session.session.query(user.User, property.PropertyGroup).join(user.User.property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)


class Test_040_PropertyGroups(PropertyDataTestBase):
    def test_0010_has_property(self):
        group1 = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        group2 = property.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()

        self.assertTrue(group1.has_property(PropertyData.prop_test1.name))
        self.assertFalse(group1.has_property(PropertyData.prop_test2.name))

        self.assertTrue(group2.has_property(PropertyData.prop_test1.name))
        self.assertTrue(group2.has_property(PropertyData.prop_test2.name))


class Test_050_Membership(PropertyDataTestBase):
    def test_0010_active_instance_property(self):
        group = property.TrafficGroup.q.filter_by(name=TrafficGroupData.group1.name).one()
        p1 = property.Membership(user=self.user, group=group)
        self.assertTrue(p1.active)
        session.session.add(p1)
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertTrue(p1.active)

        p1.disable()
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.end_date = None
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertTrue(p1.active)

        session.session.delete(p1)
        session.session.commit()

        p1 = property.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertTrue(p1.active)

        p1.start_date = datetime.utcnow() + timedelta(days=2)
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.disable()
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.end_date = p1.start_date + timedelta(days=1)
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.start_date = datetime.utcnow() - timedelta(days=1)
        session.session.commit()

        p1 = property.Membership.q.filter(property.Membership.user==self.user).filter(property.Membership.group==group).one()
        self.assertTrue(p1.active)


class Test_060_Property_Module_Code(unittest.TestCase):
    def test_0010_get_properties(self):
        property_list = property.get_properties()

        self.assertIsInstance(property_list, list)

        for item in property_list:
            self.assertIsInstance(item, basestring)

        property_set = list(set(property_list))

        # property strings have to be unique
        self.assertListEqual(sorted(property_list), sorted(property_set))
