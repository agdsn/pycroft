from fixture import DataSet, SQLAlchemyFixture, DataTestCase
from fixture.style import TrimmedNameStyle
import unittest
from datetime import datetime, timedelta
from sqlalchemy import func

from tests import OldPythonTestCase
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


class TrafficGroupData(DataSet):
    class group1:
        name = "trafficgroup1"
        traffic_limit = 1000
    class group2:
        name = "trafficgroup2"
        traffic_limit = 2000


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
#            session=session.session,
#            scoped_session=session.session._scoped_session,
            engine=session.session.get_engine() )
    return fixture


class PropertyDataTestBase(DataTestCase, OldPythonTestCase):

    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()
        cls.fixture = make_fixture()
        cls.datasets = [DormitoryData, RoomData, UserData, PropertyGroupData, TrafficGroupData, PropertyData]

    def setUp(self):
        super(PropertyDataTestBase, self).setUp()
        self.user = user.User.q.get(1)

    def tearDown(self):
        properties.Membership.q.delete()
        session.session.commit()
        super(PropertyDataTestBase, self).tearDown()
        session.session.remove()


class Test_010_PropertyResolving(PropertyDataTestBase):
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


class Test_020_MembershipValidators(PropertyDataTestBase):
    def test_0010_start_date_default(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()

        p = properties.Membership.q.first()
        self.assertIsNotNone(p)
        self.assertIsNotNone(p.start_date)
        self.assertIsNone(p.end_date)

        p1 = properties.Membership(user=self.user, group=group)
        p1.end_date = datetime.now()
        session.session.add(p1)
        session.session.commit()

    def test_0020_end_date_before_start(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        p1.start_date = datetime.now()

        def set_old_date():
            p1.end_date = datetime.now() - timedelta(hours=2)

        self.assertRaisesRegexp(AssertionError, "you set end date before start date!", set_old_date)

    def test_0030_start_date_after_end(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        p1.end_date = p1.start_date
        self.assertEqual(p1.end_date, p1.start_date)

        def set_new_start():
            p1.start_date = datetime.now() + timedelta(hours=2)

        self.assertRaisesRegexp(AssertionError, "you set start date behind end date!", set_new_start)

    def test_0040_set_correct_dates(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        p1.start_date = datetime.now()
        p1.end_date = datetime.now()
        session.session.add(p1)
        session.session.commit()

        p1.start_date = datetime.now() - timedelta(days=3)
        p1.end_date = datetime.now() + timedelta(days=3)

        session.session.commit()

    def test_0050_clear_end_date(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        p1.start_date = datetime.now()
        p1.end_date = datetime.now()
        session.session.add(p1)
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertIsNotNone(p1.end_date)

        p1.end_date = None
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertIsNone(p1.end_date)


class Test_030_View_Only_Shortcut_Properties(PropertyDataTestBase):
    def test_0010_group_users(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        self.assertEqual(len(group.users), 0)
        self.assertEqual(len(group.active_users), 0)

        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        self.assertEqual(len(group.users), 1)
        self.assertEqual(len(group.active_users), 1)

        p1.disable()
        session.session.commit()
        self.assertEqual(len(group.users), 1)
        self.assertEqual(len(group.active_users), 0)

    def test_0020_user_traffic_groups(self):
        # first have no traffic group
        group = properties.TrafficGroup.q.filter_by(name=TrafficGroupData.group1.name).one()
        self.assertEqual(len(self.user.traffic_groups), 0)
        self.assertEqual(len(self.user.active_traffic_groups), 0)

        # add one active traffic group
        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        f = properties.Membership.q.first()
        self.assertTrue(f.active)
        self.assertEqual(len(self.user.traffic_groups), 1)
        self.assertEqual(len(self.user.active_traffic_groups), 1)

        # adding a property group should not affect the traffic_groups
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 1)
        self.assertEqual(len(self.user.active_traffic_groups), 1)

        # add a second active traffic group - count should be 2
        group = properties.TrafficGroup.q.filter_by(name=TrafficGroupData.group2.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups), 2)

        # disable the second group. active should be one, all 2
        p1.disable()
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)
        self.assertEqual(len(self.user.active_traffic_groups), 1)

        # test a join
        res = session.session.query(user.User, properties.TrafficGroup.id).join(user.User.active_traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 1)
        res = session.session.query(user.User, properties.TrafficGroup.id).join(user.User.traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)

        # reenable it - but with a deadline - both counts should be 2
        p1.end_date = datetime.now() + timedelta(days=1)
        session.session.commit()
        self.assertEqual(len(self.user.traffic_groups), 2)

        # Add a second membership to the first group - should not affect the count
        group = properties.Group.q.filter_by(name=TrafficGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
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
        res = session.session.query(user.User, properties.TrafficGroup.id).join(user.User.active_traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)
        res = session.session.query(user.User, properties.TrafficGroup.id).join(user.User.traffic_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)

    def test_0030_user_property_groups(self):
        # first have no property group
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        self.assertEqual(len(self.user.property_groups), 0)
        self.assertEqual(len(self.user.active_property_groups), 0)

        # add one active property group
        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        f = properties.Membership.q.first()
        self.assertTrue(f.active)
        self.assertEqual(len(self.user.property_groups), 1)
        self.assertEqual(len(self.user.active_property_groups), 1)

        # adding a traffic group should not affect the property_group
        group = properties.TrafficGroup.q.filter_by(name=TrafficGroupData.group2.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 1)
        self.assertEqual(len(self.user.active_property_groups), 1)

        # add a second active property group - count should be 2
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()
        p1 = properties.Membership(user=self.user, group=group)
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
        res = session.session.query(user.User, properties.PropertyGroup.id).join(user.User.active_property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 1)
        res = session.session.query(user.User, properties.PropertyGroup.id).join(user.User.property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)

        # reenable it - but with a deadline - both counts should be 2
        p1.end_date = datetime.now() + timedelta(days=1)
        session.session.commit()
        self.assertEqual(len(self.user.property_groups), 2)
        self.assertEqual(len(self.user.active_property_groups), 2)

        # Add a second membership to the first group - should not affect the count
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
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
        res = session.session.query(user.User, properties.PropertyGroup).join(user.User.active_property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)
        res = session.session.query(user.User, properties.PropertyGroup).join(user.User.property_groups).filter(user.User.id==self.user.id).distinct().count()
        self.assertEqual(res, 2)


class Test_040_PropertyGroups(PropertyDataTestBase):
    def test_0010_has_property(self):
        group1 = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        group2 = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group2.name).one()

        self.assertTrue(group1.has_property(PropertyData.prop_test1.name))
        self.assertFalse(group1.has_property(PropertyData.prop_test2.name))

        self.assertTrue(group2.has_property(PropertyData.prop_test1.name))
        self.assertTrue(group2.has_property(PropertyData.prop_test2.name))


class Test_050_Membership(PropertyDataTestBase):
    def test_0010_active_instance_property(self):
        group = properties.TrafficGroup.q.filter_by(name=TrafficGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        self.assertTrue(p1.active)
        session.session.add(p1)
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertTrue(p1.active)

        p1.disable()
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.end_date = None
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertTrue(p1.active)

        session.session.delete(p1)
        session.session.commit()

        p1 = properties.Membership(user=self.user, group=group)
        session.session.add(p1)
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertTrue(p1.active)

        p1.start_date = datetime.now() + timedelta(days=2)
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.disable()
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.end_date = p1.start_date + timedelta(days=1)
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertFalse(p1.active)

        p1.start_date = datetime.now() - timedelta(days=1)
        session.session.commit()

        p1 = properties.Membership.q.filter(properties.Membership.user==self.user).filter(properties.Membership.group==group).one()
        self.assertTrue(p1.active)


