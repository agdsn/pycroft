# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.model import facilities, session, user
from pycroft.helpers.interval import single, closed
from pycroft.helpers.user import (
    generate_password, hash_password)
from pycroft.model.finance import Account
from pycroft.model.user import (
    IllegalLoginError, Membership, PropertyGroup, TrafficGroup)
from tests import FixtureDataTestBase
from tests.fixtures.dummy.facilities import BuildingData, RoomData
from tests.fixtures.dummy.property import (
    MembershipData, PropertyData, PropertyGroupData, TrafficGroupData)
from tests.fixtures.dummy.user import UserData


class Test_030_User_Passwords(FixtureDataTestBase):
    datasets = [BuildingData, RoomData, UserData]

    def setUp(self):
        super(Test_030_User_Passwords, self).setUp()
        self.user = user.User.q.filter_by(login=UserData.dummy.login).one()

    def test_0010_password_hash_validator(self):
        password = generate_password(4)
        pw_hash = hash_password(password)

        self.user.passwd_hash = pw_hash
        session.session.commit()

        with self.assertRaisesRegexp(AssertionError,
                                     "A password-hash with less than 9 chars "
                                     "is not correct!"):
            self.user.passwd_hash = password
        session.session.commit()

        with self.assertRaisesRegexp(AssertionError, "Cannot clear the "
                                                     "password hash!"):
            self.user.passwd_hash = None
        session.session.commit()

    def test_0020_set_and_verify_password(self):
        password = generate_password(4)

        self.user.set_password(password)
        session.session.commit()

        self.assertTrue(self.user.check_password(password))
        self.assertEqual(user.User.verify_and_get(self.user.login, password),
                         self.user)

        self.assertIsNone(user.User.verify_and_get(self.user.login,
                                                   password + "_wrong"))

        for length in range(4, 10):
            for cnt in range(1, 3):
                pw = generate_password(length)
                if pw == password:
                    continue
                self.assertFalse(self.user.check_password(pw))
                self.assertIsNone(user.User.verify_and_get(self.user.login, pw))


class Test_040_User_Login(FixtureDataTestBase):
    datasets = [BuildingData, RoomData, UserData]

    def test_0010_user_login_validator(self):
        account = Account(name='', type='ASSET')
        u = user.User(name="John Doe",
                      registered_at=session.utcnow(),
                      room=facilities.Room.q.first(),
                      account=account)

        def set_login(login):
            u.login = login

        for length in range(1, 30):
            if 2 <= length < 23:
                set_login("a" * length)
            else:
                self.assertRaisesRegexp(IllegalLoginError, "invalid unix-login.*",
                                        set_login, "a" * length)

        valid = ["abcdefg", "a_b", "a3b", "a_2b", "a33", "a_4"]
        invalid = ["123", "ABC", "3bc", "_ab", "ab_", "3b_", "_b3", "&&"]
        blocked = ["root", "daemon", "bin", "sys", "sync", "games", "man",
                   "lp", "mail", "news", "uucp", "proxy", "majordom",
                   "postgres", "wwwadmin", "backup", "msql", "operator",
                   "ftp", "ftpadmin", "guest", "bb", "nobody"]

        for login in valid:
            set_login(login)
        for login in invalid:
            self.assertRaisesRegexp(Exception, "invalid unix-login.*",
                                    set_login, login)
        for login in blocked:
            self.assertRaisesRegexp(Exception, "invalid unix-login.*",
                                    set_login, login)

        u = user.User.q.filter_by(login=UserData.dummy.login).one()
        self.assertRaisesRegexp(
            AssertionError,
            "user already in the database - cannot change login anymore!",
            set_login, "abc")

        session.session.commit()


class TestActiveHybridMethods(FixtureDataTestBase):
    datasets = [UserData, PropertyGroupData, TrafficGroupData]

    def setUp(self):
        super(TestActiveHybridMethods, self).setUp()
        self.user = user.User.q.filter_by(login=UserData.dummy.login).one()
        self.property_group = PropertyGroup.q.filter_by(
            name=PropertyGroupData.dummy.name).one()
        self.traffic_group = TrafficGroup.q.filter_by(
            name=TrafficGroupData.dummy.name).one()

    def add_membership(self, group):
        m = Membership(user=self.user, group=group)
        session.session.add(m)
        session.session.commit()
        return m

    def test_active_memberships(self):
        self.assertEqual(self.user.active_memberships(), [])
        m = self.add_membership(self.property_group)
        self.assertEqual(self.user.active_memberships(), [m])
        when = single(session.utcnow() - timedelta(hours=1))
        self.assertEqual(self.user.active_memberships(when), [])
        when = single(session.utcnow() + timedelta(hours=1))
        self.assertEqual(self.user.active_memberships(when), [m])

    def create_active_memberships_query(self, when=None):
        return session.session.query(Membership).from_statement(
            user.User.active_memberships(when).where(
                user.User.id == self.user.id))

    def test_active_memberships_expression(self):
        query = self.create_active_memberships_query()
        self.assertEqual(query.all(), [])
        m = self.add_membership(self.property_group)
        query = self.create_active_memberships_query()
        self.assertEqual(query.all(), [m])
        when = single(session.utcnow() - timedelta(hours=1))
        query = self.create_active_memberships_query(when)
        self.assertEqual(query.all(), [])
        when = single(session.utcnow() + timedelta(hours=1))
        query = self.create_active_memberships_query(when)
        self.assertEqual(query.all(), [m])

    def test_active_property_groups(self):
        self.assertEqual(self.user.active_property_groups(), [])
        self.add_membership(self.property_group)
        self.assertEqual(self.user.active_property_groups(),
                         [self.property_group])
        when = single(session.utcnow() - timedelta(hours=1))
        self.assertEqual(self.user.active_property_groups(when), [])
        when = single(session.utcnow() + timedelta(hours=1))
        self.assertEqual(self.user.active_property_groups(when),
                         [self.property_group])

    def create_active_property_groups_query(self, when=None):
        return session.session.query(PropertyGroup).from_statement(
            user.User.active_property_groups(when).where(
                user.User.id == self.user.id))

    def test_active_property_groups_expression(self):
        query = self.create_active_property_groups_query()
        self.assertEqual(query.all(), [])
        self.add_membership(self.property_group)
        query = self.create_active_property_groups_query()
        self.assertEqual(query.all(), [self.property_group])
        when = single(session.utcnow() - timedelta(hours=1))
        query = self.create_active_property_groups_query(when)
        self.assertEqual(query.all(), [])
        when = single(session.utcnow() + timedelta(hours=1))
        query = self.create_active_property_groups_query(when)
        self.assertEqual(query.all(), [self.property_group])

    def test_active_traffic_groups(self):
        self.assertEqual(self.user.active_traffic_groups(), [])
        self.add_membership(self.traffic_group)
        self.assertEqual(self.user.active_traffic_groups(),
                         [self.traffic_group])
        when = single(session.utcnow() - timedelta(hours=1))
        self.assertEqual(self.user.active_traffic_groups(when), [])
        when = single(session.utcnow() + timedelta(hours=1))
        self.assertEqual(self.user.active_traffic_groups(when),
                         [self.traffic_group])

    def create_active_traffic_groups_query(self, when=None):
        return session.session.query(TrafficGroup).from_statement(
            user.User.active_traffic_groups(when).where(
                user.User.id == self.user.id))

    def test_active_traffic_groups_expression(self):
        query = self.create_active_traffic_groups_query()
        self.assertEqual(query.all(), [])
        self.add_membership(self.traffic_group)
        query = self.create_active_traffic_groups_query()
        self.assertEqual(query.all(), [self.traffic_group])
        when = single(session.utcnow() - timedelta(hours=1))
        query = self.create_active_traffic_groups_query(when)
        self.assertEqual(query.all(), [])
        when = single(session.utcnow() + timedelta(hours=1))
        query = self.create_active_traffic_groups_query(when)
        self.assertEqual(query.all(), [self.traffic_group])


class Test_has_property(FixtureDataTestBase):

    datasets = [MembershipData, PropertyData, PropertyGroupData, UserData]

    def setUp(self):
        super(Test_has_property, self).setUp()
        self.user = user.User.q.filter_by(login=UserData.dummy.login).one()

    def test_positive_test(self):
        self.assertTrue(self.user.has_property(PropertyData.granted.name))
        self.assertIsNotNone(
            user.User.q.filter(
                user.User.login == self.user.login,
                user.User.has_property(PropertyData.granted.name)
            ).first())

    def test_negative_test(self):
        self.assertFalse(self.user.has_property(PropertyData.denied.name))
        self.assertIsNone(
            user.User.q.filter(
                user.User.login == self.user.login,
                user.User.has_property(PropertyData.denied.name)
            ).first())

    def test_non_existent_test(self):
        self.assertFalse(self.user.has_property("unused"))
        self.assertIsNone(
            user.User.q.filter(
                user.User.login == self.user.login,
                user.User.has_property("unused")
            ).first())

    def test_positive_test_interval(self):
        interval = closed(MembershipData.dummy_membership.begins_at,
                          MembershipData.dummy_membership.ends_at)
        self.assertTrue(
            self.user.has_property(PropertyData.granted.name, interval)
        )
        self.assertIsNotNone(
            user.User.q.filter(
                user.User.login == self.user.login,
                user.User.has_property(PropertyData.granted.name, interval)
            ).first())

    def test_negative_test_interval(self):
        interval = closed(
            MembershipData.dummy_membership.ends_at + timedelta(1),
            MembershipData.dummy_membership.ends_at + timedelta(2)
        )
        self.assertFalse(
            self.user.has_property(PropertyData.granted.name, interval)
        )
        self.assertIsNone(
            user.User.q.filter(
                user.User.login == self.user.login,
                user.User.has_property(PropertyData.granted.name, interval)
            ).first())
