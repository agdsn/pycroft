# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import random
import unittest
from crypt import crypt as python_crypt
from datetime import timedelta

from passlib.hash import ldap_salted_sha1, ldap_md5_crypt, ldap_sha1_crypt

from pycroft.model import facilities, session, property, user
from pycroft.helpers.interval import single, closed
from pycroft.helpers.user import (
    generate_password, hash_password, verify_password, generate_crypt_salt)
from pycroft.model.finance import FinanceAccount
from tests import FixtureDataTestBase
from tests.fixtures.dummy.dormitory import DormitoryData, RoomData
from tests.fixtures.dummy.property import (
    MembershipData, PropertyData, PropertyGroupData, TrafficGroupData)
from tests.fixtures.dummy.user import UserData


class Test_010_PasswordGenerator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(Test_010_PasswordGenerator, self).__init__(*args, **kwargs)
        self.pws = []

    def test_0010_pw_length(self):
        for i in range(0, 100):
            length = random.randint(2, 12)
            pw = generate_password(length)
            self.assertEqual(len(pw), length)
            self.pws.append(pw)

    def test_0020_unique(self):
        for i in range(0, 100):
            self.pws.append(generate_password(8))

        self.assertEqual(len(self.pws), len(set(self.pws)))

    def test_0030_first_part_unique(self):
        pws = list(self.pws)
        pws = filter(lambda x: len(x) >= 6, pws)
        self.assertEqual(len(set(map(lambda x: x[:6], pws))), len(pws))


class Test_020_PasswdHashes(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        self.hashes = []

        def crypt_pw(pw):
            return "{crypt}" + python_crypt(pw, generate_crypt_salt(2))

        self.methods = {"crypt": crypt_pw,
                        "CRYPT": ldap_sha1_crypt.encrypt,
                        "MD5": ldap_md5_crypt.encrypt,
                        "SSHA": ldap_salted_sha1.encrypt}

        for length in range(4,20):
            pw = generate_password(length)
            hash_dict = {"plain": pw}
            for method in self.methods:
                hash_dict[method] = self.methods[method](pw)
            self.hashes.append(hash_dict)
        super(Test_020_PasswdHashes, self).__init__(*args, **kwargs)

    def test_0010_verify(self):
        for pw in self.hashes:
            for method in self.methods:
                self.assertTrue(verify_password(pw["plain"],  pw[method]), "{}: '{}' should verify with '{}'".format(method, pw[method], pw["plain"]))
                self.assertFalse(verify_password(pw["plain"], pw[method][len(method)+2:]))

    def test_0020_generate_hash(self):
        cur_type = "SSHA"
        for pw in self.hashes:
            self.assertNotEqual(hash_password(pw["plain"]), pw[cur_type], "Salt should be different!")
            self.assertTrue(hash_password(pw["plain"]).startswith("{{{}}}".format(cur_type)))

    def test_0030_generate_plain(self):
        pw_list = []
        hash_list = []
        for num in range(1, 500):
            pw = generate_password(9)
            self.assertEqual(len(pw), 9)
            self.assertFalse(pw in pw_list)
            pw_list.append(pw)
            pw_hash = hash_password(pw)
            self.assertFalse(pw_hash in hash_list)
            hash_list.append(pw_hash)

class Test_030_User_Passwords(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData]

    def test_0010_password_hash_validator(self):
        u = user.User.q.filter_by(login=UserData.dummy.login).one()
        password = generate_password(4)
        pw_hash = hash_password(password)

        def set_hash(h):
            u.passwd_hash = h

        set_hash(pw_hash)
        session.session.commit()

        self.assertRaisesRegexp(AssertionError, "A password-hash with les than 9 chars is not correct!", set_hash, password)
        session.session.commit()

        self.assertRaisesRegexp(AssertionError, "Cannot clear the password hash!", set_hash, None)
        session.session.commit()

    def test_0020_set_and_verify_password(self):
        u = user.User.q.filter_by(login=UserData.dummy.login).one()
        password = generate_password(4)
        pw_hash = hash_password(password)

        u.set_password(password)
        session.session.commit()

        u = user.User.q.filter_by(login=UserData.dummy.login).one()
        self.assertTrue(u.check_password(password))
        self.assertIsNotNone(user.User.verify_and_get(u.login, password))
        self.assertEqual(user.User.verify_and_get(u.login, password), u)

        self.assertIsNone(user.User.verify_and_get(password, u.login))

        for length in range(0, 10):
            for cnt in range(1, 3):
                pw = generate_password(length)
                if pw != password:
                    self.assertFalse(u.check_password(pw))
                    self.assertIsNone(user.User.verify_and_get(u.login, pw))


class Test_040_User_Login(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData]

    def test_0010_user_login_validator(self):
        finance_account = FinanceAccount(name='', type='ASSET')
        u = user.User(name="John Doe",
                      registered_at=session.utcnow(),
                      room=facilities.Room.q.first(),
                      finance_account=finance_account
        )

        def set_login(login):
            u.login = login

        for length in range(1, 30):
            if 2 < length < 23:
                set_login("a" * length)
            else:
                self.assertRaisesRegexp(Exception, "invalid unix-login!",
                                        set_login, "a" * length)

        valid = ["abcdefg", "a_b", "a3b", "a_2b", "a33", "a__4"]
        invalid = ["123", "ABC", "3bc", "_ab", "ab_", "3b_", "_b3", "&&"]
        blocked = ["root", "daemon", "bin", "sys", "sync", "games", "man",
                   "lp", "mail", "news", "uucp", "proxy", "majordom",
                   "postgres", "wwwadmin", "backup", "msql", "operator",
                   "ftp", "ftpadmin", "guest", "bb", "nobody"]

        for login in valid:
            set_login(login)
        for login in invalid:
            self.assertRaisesRegexp(Exception, "invalid unix-login!",
                                    set_login, login)
        for login in blocked:
            self.assertRaisesRegexp(Exception, "invalid unix-login!",
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
        self.property_group = property.PropertyGroup.q.filter_by(
            name=PropertyGroupData.dummy.name).one()
        self.traffic_group = property.TrafficGroup.q.filter_by(
            name=TrafficGroupData.dummy.name).one()

    def add_membership(self, group):
        m = property.Membership(user=self.user, group=group)
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
        return session.session.query(property.Membership).from_statement(
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
        return session.session.query(property.PropertyGroup).from_statement(
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
        return session.session.query(property.TrafficGroup).from_statement(
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
