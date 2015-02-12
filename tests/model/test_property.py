# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from tests import FixtureDataTestBase
from pycroft.model import session, user, property
from tests.fixtures.dummy.facilities import (DormitoryData, RoomData)
from tests.fixtures.dummy.user import UserData
from tests.model.property_fixtures import (
    PropertyData, PropertyGroupData, TrafficGroupData)


class PropertyDataTestBase(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, PropertyGroupData,
                TrafficGroupData, PropertyData]

    def setUp(self):
        super(PropertyDataTestBase, self).setUp()
        self.user = user.User.q.filter_by(login=UserData.dummy.login).one()
        self.property_group1 = property.PropertyGroup.q.filter_by(
            name=PropertyGroupData.group1.name).one()
        self.property_group2 = property.PropertyGroup.q.filter_by(
            name=PropertyGroupData.group2.name).one()
        self.traffic_group1 = property.TrafficGroup.q.filter_by(
            name=TrafficGroupData.group1.name).one()
        self.traffic_group2 = property.TrafficGroup.q.filter_by(
            name=TrafficGroupData.group2.name).one()

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

        self.assertEqual(len(self.property_group1.properties), 1)
        self.assertEqual(len(self.property_group2.properties), 2)
        self.assertIn(PropertyData.prop_test1.name, self.property_group1.properties)
        self.assertIn(PropertyData.prop_test1.name, self.property_group2.properties)
        self.assertIn(PropertyData.prop_test2.name, self.property_group2.properties)

    def test_0020_add_membership(self):
        # add membership to group1
        membership = property.Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group1
        )
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        # add membership to group2
        membership = property.Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group2
        )
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertTrue(self.user.has_property(PropertyData.prop_test2.name))

    def test_0030_add_timed_membership(self):
        # add membership to group1
        now = session.utcnow()
        membership = property.Membership(
            begins_at=now,
            user=self.user,
            group=self.property_group1
        )
        membership.ends_at = membership.begins_at + timedelta(days=3)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

        # add expired membership to group2
        membership = property.Membership(
            begins_at=now - timedelta(hours=2),
            user=self.user,
            group=self.property_group2
        )
        membership.ends_at = now - timedelta(hours=1)
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        self.assertFalse(self.user.has_property(PropertyData.prop_test2.name))

    def test_0040_disable_membership(self):
        # add membership to group1
        membership = property.Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group1
        )
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))
        membership.disable()
        session.session.commit()
        self.assertNotIn(
            self.property_group1,
            self.user.active_property_groups()
        )
        self.assertFalse(self.user.has_property(PropertyData.prop_test1.name))

        # add membership to group1
        membership = property.Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group1
        )
        session.session.add(membership)
        session.session.commit()

        self.assertTrue(self.user.has_property(PropertyData.prop_test1.name))

        # add membership to group2
        membership = property.Membership(
            begins_at=session.utcnow(),
            user=self.user,
            group=self.property_group2
        )
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
        # add membership to group1
        p1 = property.Membership(user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()

        p = property.Membership.q.first()
        self.assertIsNotNone(p)
        self.assertIsNotNone(p.begins_at)
        self.assertIsNone(p.ends_at)

    def test_0020_end_date_before_start(self):
        # add membership to group1
        p1 = property.Membership(user=self.user, group=self.property_group1)
        p1.begins_at = session.utcnow()

        def set_old_date():
            """ Set ends_at before begins_at
            """
            p1.ends_at = session.utcnow() - timedelta(hours=2)

        self.assertRaisesRegexp(
            AssertionError,
            "begins_at must be before ends_at",
            set_old_date
        )

    def test_0030_start_date_after_end(self):
        # add membership to group1
        now = session.utcnow()
        self.assertRaisesRegexp(
            AssertionError,
            "begins_at must be before ends_at",
            property.Membership, user=self.user, group=self.property_group1,
            begins_at=now + timedelta(days=1), ends_at=now
        )

    def test_0040_set_correct_dates(self):
        # add membership to group1
        p1 = property.Membership(user=self.user, group=self.property_group1)
        p1.begins_at = session.utcnow()
        p1.ends_at = session.utcnow()

        session.session.add(p1)
        session.session.commit()

        p1.begins_at = session.utcnow() - timedelta(days=3)
        p1.ends_at = session.utcnow() + timedelta(days=3)

        session.session.commit()

    def test_0050_clear_end_date(self):
        # add membership to group1
        p1 = property.Membership(user=self.user, group=self.property_group1)
        p1.begins_at = session.utcnow()
        p1.ends_at = session.utcnow()
        session.session.add(p1)
        session.session.commit()

        # test if membership in database
        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertIsNotNone(p1.ends_at)

        # clear ends_at
        p1.ends_at = None
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertIsNone(p1.ends_at)


class Test_030_View_Only_Shortcut_Properties(PropertyDataTestBase):
    def test_0010_group_users(self):
        self.assertEqual(len(self.property_group1.users), 0)
        self.assertEqual(len(self.property_group1.active_users()), 0)

        # add membership to group1
        p1 = property.Membership(user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()

        self.assertEqual(len(self.property_group1.users), 1)
        self.assertEqual(len(self.property_group1.active_users()), 1)

        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.property_group1.users), 1)
        self.assertEqual(len(self.property_group1.active_users()), 0)

    def test_0020_user_traffic_groups(self):
        # first have no traffic group
        self.assertEqual(len(self.user.traffic_groups), 0)
        self.assertEqual(len(self.user.active_traffic_groups()), 0)

        # add one active traffic group
        p1 = property.Membership(user=self.user, group=self.traffic_group1)
        session.session.add(p1)
        session.session.commit()
        f = property.Membership.q.first()
        self.assertTrue(f.active())
        self.assertEqual(len(self.user.traffic_groups), 1)
        self.assertEqual(len(self.user.active_traffic_groups()), 1)

        # adding a property group should not affect the traffic_groups
        p1 = property.Membership(user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 1)
        self.assertEqual(len(self.user.active_traffic_groups()), 1)

        # add a second active traffic group - count should be 2
        p2 = property.Membership(user=self.user, group=self.traffic_group2)
        session.session.add(p2)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups()), 2)

        # disable the second group. active should be one, all 2
        p2.disable()
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups()), 1)

        res = session.session.query(
            user.User, property.TrafficGroup.id
        ).join(
            user.User.traffic_groups
        ).filter(
            user.User.id == self.user.id
        ).distinct().count()
        self.assertEqual(res, 2)

        # reenable it - but with a deadline - both counts should be 2
        p2.ends_at = session.utcnow() + timedelta(days=1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups()), 2)

        # Add a second membership to the first group
        # should not affect the count
        p1 = property.Membership(user=self.user, group=self.traffic_group1)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups()), 2)

        # disabling the new one should also not affect.
        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups()), 2)

        res = session.session.query(
            user.User, property.TrafficGroup.id
        ).join(
            user.User.traffic_groups
        ).filter(
            user.User.id == self.user.id
        ).distinct().count()
        self.assertEqual(res, 2)

    def test_0030_user_property_groups(self):
        # first have no property group
        self.assertEqual(len(self.user.property_groups), 0)
        self.assertEqual(len(self.user.active_property_groups()), 0)

        # add one active property group
        p1 = property.Membership(user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()
        f = property.Membership.q.first()
        self.assertTrue(f.active())
        self.assertEqual(len(self.user.property_groups), 1)
        self.assertEqual(len(self.user.active_property_groups()), 1)

        # adding a traffic group should not affect the property_group
        p1 = property.Membership(user=self.user, group=self.traffic_group2)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 1)
        self.assertEqual(len(self.user.active_property_groups()), 1)

        # add a second active property group - count should be 2
        p1 = property.Membership(user=self.user, group=self.property_group2)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups()), 2)

        # disable the second group. active should be one, all 2
        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups()), 1)

        # test a join
        res = session.session.query(
            user.User, property.PropertyGroup.id
        ).join(user.User.property_groups).filter(
            user.User.id == self.user.id
        ).distinct().count()
        self.assertEqual(res, 2)

        # reenable it - but with a deadline - both counts should be 2
        p1.ends_at = session.utcnow() + timedelta(days=1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups()), 2)

        # Add a second membership to the first group
        # should not affect the count
        p1 = property.Membership(user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups()), 2)

        # disabling the new one should also not affect.
        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups()), 2)

        # test a join
        res = session.session.query(
            user.User, property.PropertyGroup
        ).join(user.User.property_groups).filter(
            user.User.id == self.user.id
        ).distinct().count()
        self.assertEqual(res, 2)


class Test_050_Membership(PropertyDataTestBase):
    def test_0010_active_instance_property(self):
        p1 = property.Membership(user=self.user, group=self.property_group1)
        self.assertTrue(p1.active())
        session.session.add(p1)
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertTrue(p1.active())

        p1.disable()
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertFalse(p1.active())

        p1.ends_at = None
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertTrue(p1.active())

        session.session.delete(p1)
        session.session.commit()

        p1 = property.Membership(user=self.user, group=self.property_group1)
        session.session.add(p1)
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertTrue(p1.active())

        p1.begins_at = session.utcnow() + timedelta(days=2)
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertFalse(p1.active())

        p1.disable()
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertFalse(p1.active())

        p1.ends_at = p1.begins_at + timedelta(days=1)
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertFalse(p1.active())

        p1.begins_at = session.utcnow() - timedelta(days=1)
        session.session.commit()

        p1 = property.Membership.q.filter_by(
            user=self.user, group=self.property_group1
        ).one()
        self.assertTrue(p1.active())


class TestGroup(PropertyDataTestBase):
    def add_membership(self):
        session.session.add(property.Membership(user=self.user,
                                                group=self.property_group1))
        session.session.commit()

    def test_active_users(self):
        self.assertEqual(self.property_group1.active_users(), [])
        self.add_membership()
        self.assertEqual(self.property_group1.active_users(), [self.user])

    def create_active_users_query(self):
        active_users = property.Group.active_users().where(
            property.Group.id == self.property_group1.id)
        return session.session.query(user.User).from_statement(active_users)

    def test_active_users_expression(self):
        query = self.create_active_users_query()
        self.assertEqual(query.all(), [])
        self.add_membership()
        query = self.create_active_users_query()
        self.assertEqual(query.all(), [self.user])
