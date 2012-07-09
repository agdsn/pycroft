from fixture import DataSet, SQLAlchemyFixture, DataTestCase
from fixture.style import TrimmedNameStyle
import unittest
from datetime import datetime, timedelta

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
        cls.datasets = [DormitoryData, RoomData, UserData, PropertyGroupData, PropertyData]

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
        p1.end_date = datetime.now()
        self.assertEqual(p1.end_date, p1.start_date)

        def set_new_start():
            p1.start_date = datetime.now() + timedelta(hours=2)

        self.assertRaisesRegexp(AssertionError, "you set start date behind end date!", set_new_start)

    def test_0040_set_correct_dates(self):
        group = properties.PropertyGroup.q.filter_by(name=PropertyGroupData.group1.name).one()
        p1 = properties.Membership(user=self.user, group=group)
        p1.start_date = datetime.now()
        p1.end_date = datetime.now()

        p1.start_date = datetime.now() - timedelta(days=3)
        p1.end_date = datetime.now() + timedelta(days=3)

        session.session.add(p1)
        session.session.commit()
