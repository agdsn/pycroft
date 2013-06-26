from tests import FixtureDataTestBase
from tests.lib.fixtures.property_fixtures import UserData, PropertyGroupData,\
    PropertyData, MembershipData, TrafficGroupData

from pycroft.lib.property import create_membership, create_property,\
    create_property_group, create_traffic_group, delete_membership,\
    delete_property, delete_property_group, delete_traffic_group, _create_group,\
    _delete_group

from pycroft.model.property import TrafficGroup, PropertyGroup, Property,\
    Membership, Group
from pycroft.model.user import User
from pycroft.model import session

from datetime import datetime
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

    def test_0020_delete_property_group(self):
        del_property_group = delete_property_group(
            PropertyGroupData.dummy_property_group1.id)

        self.assertIsNone(PropertyGroup.q.get(del_property_group.id))

    def test_0025_delete_wrong_property_group(self):
        self.assertRaises(ValueError, delete_property_group,
            PropertyGroupData.dummy_property_group1.id + 100)


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

    def test_0020_delete_traffic_group(self):
        del_traffic_group = delete_traffic_group(
            TrafficGroupData.dummy_traffic_group1.id)

        self.assertIsNone(TrafficGroup.q.get(del_traffic_group.id))

    def test_0025_delete_wrong_traffic_group(self):
        self.assertRaises(ValueError, delete_traffic_group,
            TrafficGroupData.dummy_traffic_group1.id + 100)


class Test_030_Membership(FixtureDataTestBase):
    datasets = [MembershipData, PropertyGroupData, UserData]

    def test_0010_create_membership(self):
        start_date = datetime.now()
        end_date = datetime.now()
        group = PropertyGroup.q.first()
        user = User.q.first()

        membership = create_membership(start_date=start_date, end_date=end_date,
            group_id=group.id, user_id=user.id)

        self.assertIsNotNone(Membership.q.get(membership.id))

        db_membership = Membership.q.get(membership.id)

        self.assertEqual(db_membership.start_date, start_date)
        self.assertEqual(db_membership.end_date, end_date)
        self.assertEqual(db_membership.group, group)
        self.assertEqual(db_membership.user, user)

        session.session.delete(db_membership)
        session.session.commit()

    def test_0020_delete_membership(self):
        del_membership = delete_membership(MembershipData.dummy_membership1.id)

        self.assertIsNone(Membership.q.get(del_membership.id))

    def test_0025_delete_wrong_membership(self):
        self.assertRaises(ValueError, delete_membership,
            MembershipData.dummy_membership1.id + 100)


class Test_040_Property(FixtureDataTestBase):
    datasets = [PropertyGroupData, PropertyData]

    def test_0010_create_property(self):
        name = "dummy_property2"
        property_group = PropertyGroup.q.first()

        (_, property) = create_property(property_group_id=property_group.id,
                                        name=name, granted=True)

        self.assertIsNotNone(Property.q.get(property.id))

        db_property = Property.q.get(property.id)

        self.assertEqual(db_property.name, name)
        self.assertEqual(db_property.property_group, property_group)

        session.session.delete(db_property)
        session.session.commit()

    def test_0015_create_wrong_property(self):
        name = "dummy_property3"
        property_group_id = PropertyData.dummy_property1.property_group.id

        self.assertRaises(ValueError, create_property,
                          property_group_id=property_group_id + 100,
                          name=name,
                          granted=True)

    def test_0020_delete_property(self):
        property_name = PropertyData.dummy_property1.name
        group_id = PropertyData.dummy_property1.property_group.id

        (_, del_property) = delete_property(property_group_id=group_id,
                                            name=property_name)

        self.assertIsNone(Property.q.get(del_property.id))

    def test_0025_delete_wrong_property(self):
        property_name = PropertyData.dummy_property1.name
        group_id = PropertyData.dummy_property1.property_group.id
        empty_group_id = PropertyGroupData.dummy_property_group2.id

        self.assertRaises(ValueError, delete_property,
                          property_group_id=group_id,
                          name=property_name + "_fail")
        self.assertRaises(ValueError, delete_property,
                          property_group_id=group_id + 100,
                          name=property_name)
        self.assertRaises(ValueError, delete_property,
                          property_group_id=empty_group_id,
                          name=property_name)


class Test_050_MalformedGroup(FixtureDataTestBase):
    datasets = [UserData]

    class MalformedGroup(Group):
        id = Column(Integer, ForeignKey("group.id"), primary_key=True)
        __mapper_args__ = {'polymorphic_identity': 'malformed_group'}

    def test_0010_create_malformed_group(self):
        name = "malformed_group1"

        self.assertRaises(ValueError, _create_group, type='malformed_group',
            name=name, id=100)

    def test_0020_delete_malformed_group(self):
        malformed_group = Test_050_MalformedGroup.MalformedGroup(id=1000,
            name="malformed_group2")

        session.session.add(malformed_group)
        session.session.commit()

        self.assertRaises(ValueError, _delete_group, malformed_group.id)

        session.session.delete(malformed_group)
        session.session.commit()

