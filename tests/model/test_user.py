# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.helpers.interval import single, closed
from pycroft.helpers.user import generate_password, hash_password
from pycroft.model import session, user
from pycroft.model.finance import Account
from pycroft.model.user import IllegalLoginError, Membership, PropertyGroup, User
from tests import FactoryDataTestBase, factories


class Test_User_Passwords(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = factories.UserFactory()

    def test_password_hash_validator(self):
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

    def test_set_and_verify_password(self):
        password = generate_password(4)

        self.user.password = password
        session.session.commit()

        assert self.user.check_password(password)
        assert user.User.verify_and_get(self.user.login, password) == self.user

        assert user.User.verify_and_get(self.user.login, password + "_wrong") is None

        for length in range(4, 10):
            for cnt in range(1, 3):
                pw = generate_password(length)
                if pw == password:
                    continue
                assert not self.user.check_password(pw)
                assert user.User.verify_and_get(self.user.login, pw) is None


class Test_User_Login(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.room = factories.RoomFactory()
        self.user = factories.UserFactory()

    def test_user_login_validator(self):
        account = Account(name='', type='ASSET')
        room = self.room
        u = user.User(name="John Doe",
                      registered_at=session.utcnow(),
                      room=room,
                      address=room.address,
                      account=account)

        for length in range(1, 30):
            if 2 <= length < 23:
                u.login = "a" * length
            else:
                with self.assertRaises(IllegalLoginError):
                    u.login = "a" * length

        valid = ["abcdefg", "a-b", "a3b", "a.2b", "a33", "a-4"]
        invalid = ["123", "ABC", "3bc", "_ab", "ab_", "3b_", "_b3", "&&",
                   "a_b", "a_2b", "a_4", "-ab", "ab-", ".ab", "ab."]
        blocked = ["abuse", "admin", "administrator", "autoconfig",
                   "broadcasthost", "root", "daemon", "bin", "sys", "sync",
                   "games", "man", "hostmaster", "imap", "info", "is",
                   "isatap", "it", "localdomain", "localhost",
                   "lp", "mail", "mailer-daemon", "news", "uucp", "proxy",
                   "majordom", "marketing", "mis", "noc", "website", "api"
                   "noreply", "no-reply", "pop", "pop3", "postmaster",
                   "postgres", "sales", "smtp", "ssladmin", "status",
                   "ssladministrator", "sslwebmaster", "support",
                   "sysadmin", "usenet", "webmaster", "wpad", "www",
                   "wwwadmin", "backup", "msql", "operator", "user",
                   "ftp", "ftpadmin", "guest", "bb", "nobody", "www-data",
                   "bacula", "contact", "email", "privacy", "anonymous",
                   "web", "git", "username", "log", "login", "help", "name"]

        for login in valid:
            u.login = login
        for login in invalid:
            with self.assertRaises(IllegalLoginError):
                u.login = login
        for login in blocked:
            with self.assertRaises(IllegalLoginError):
                u.login = login

    def test_login_cannot_be_changed(self):
        with self.assertRaisesRegexp(AssertionError,
                "user already in the database - cannot change login anymore!"):
            self.user.login = "abc"

    def test_user_login_case_insensitive(self):
        u = self.user

        password = 'secret'
        u.password = password
        session.session.commit()

        assert user.User.verify_and_get(u.login, password) == u

        # Verification of login name should be case insensitive
        assert user.User.verify_and_get(u.login.upper(), password) == u

class TestUnixAccounts(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.ldap_user = factories.UserFactory(with_unix_account=True)
        self.dummy_user = factories.UserFactory()

        self.custom_account = factories.UnixAccountFactory(gid=27)
        self.dummy_account = factories.UnixAccountFactory()

    def test_correct_default_values(self):
        assert self.dummy_account.gid == 100
        assert self.dummy_account.uid >= 1000
        assert self.dummy_account.login_shell

    def test_custom_ids_set(self):
        assert self.custom_account.gid == 27

    def test_account_reference(self):
        assert isinstance(self.ldap_user.unix_account, user.UnixAccount)
        assert self.ldap_user.unix_account.home_directory.startswith('/home/')
        assert self.dummy_user.unix_account is None


class TestActiveHybridMethods(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = factories.UserFactory()
        self.property_group = factories.PropertyGroupFactory()

    def add_membership(self, group):
        m = Membership(user=self.user, group=group)
        session.session.add(m)
        session.session.commit()
        return m

    def test_active_memberships(self):
        assert self.user.active_memberships() == []
        m = self.add_membership(self.property_group)
        assert self.user.active_memberships() == [m]
        when = single(session.utcnow() - timedelta(hours=1))
        assert self.user.active_memberships(when) == []
        when = single(session.utcnow() + timedelta(hours=1))
        assert self.user.active_memberships(when) == [m]

    def create_active_memberships_query(self, when=None):
        return session.session.query(Membership).from_statement(
            user.User.active_memberships(when).where(
                user.User.id == self.user.id))

    def test_active_memberships_expression(self):
        query = self.create_active_memberships_query()
        assert query.all() == []
        m = self.add_membership(self.property_group)
        query = self.create_active_memberships_query()
        assert query.all() == [m]
        when = single(session.utcnow() - timedelta(hours=1))
        query = self.create_active_memberships_query(when)
        assert query.all() == []
        when = single(session.utcnow() + timedelta(hours=1))
        query = self.create_active_memberships_query(when)
        assert query.all() == [m]

    def test_active_property_groups(self):
        assert self.user.active_property_groups() == []
        self.add_membership(self.property_group)
        assert self.user.active_property_groups() == [self.property_group]
        when = single(session.utcnow() - timedelta(hours=1))
        assert self.user.active_property_groups(when) == []
        when = single(session.utcnow() + timedelta(hours=1))
        assert self.user.active_property_groups(when) == [self.property_group]

    def create_active_property_groups_query(self, when=None):
        return session.session.query(PropertyGroup).from_statement(
            user.User.active_property_groups(when).where(
                user.User.id == self.user.id))

    def test_active_property_groups_expression(self):
        query = self.create_active_property_groups_query()
        assert query.all() == []
        self.add_membership(self.property_group)
        query = self.create_active_property_groups_query()
        assert query.all() == [self.property_group]
        when = single(session.utcnow() - timedelta(hours=1))
        query = self.create_active_property_groups_query(when)
        assert query.all() == []
        when = single(session.utcnow() + timedelta(hours=1))
        query = self.create_active_property_groups_query(when)
        assert query.all() == [self.property_group]


class Test_has_property(FactoryDataTestBase):
    GRANTED_NAME = 'granted'
    DENIED_NAME = 'denied'

    def create_factories(self):
        super().create_factories()
        self.user = factories.UserFactory()
        group = factories.PropertyGroupFactory(granted={self.GRANTED_NAME},
                                               denied={self.DENIED_NAME})
        self.membership = factories.MembershipFactory(group=group, user=self.user,
                                                      includes_today=True)

    def test_positive_test(self):
        assert self.user.has_property(self.GRANTED_NAME)
        assert user.User.q.filter(
            user.User.login == self.user.login,
            user.User.has_property(self.GRANTED_NAME)
        ).first() is not None

    def test_negative_test(self):
        assert not self.user.has_property(self.DENIED_NAME)
        assert user.User.q.filter(
            user.User.login == self.user.login,
            user.User.has_property(self.DENIED_NAME)
        ).first() is None

    def test_non_existent_test(self):
        assert not self.user.has_property("unused")
        assert user.User.q.filter(
            user.User.login == self.user.login,
            user.User.has_property("unused")
        ).first() is None

    def test_positive_test_interval(self):
        interval = closed(self.membership.begins_at,
                          self.membership.ends_at)
        assert self.user.has_property(self.GRANTED_NAME, interval)
        assert user.User.q.filter(
            user.User.login == self.user.login,
            user.User.has_property(self.GRANTED_NAME, interval)
        ).first() is not None

    def test_negative_test_interval(self):
        interval = closed(
            self.membership.ends_at + timedelta(1),
            self.membership.ends_at + timedelta(2)
        )
        assert not self.user.has_property(self.GRANTED_NAME, interval)
        assert user.User.q.filter(
            user.User.login == self.user.login,
            user.User.has_property(self.GRANTED_NAME, interval)
        ).first() is None


class UserAddressTest(FactoryDataTestBase):
    def assert_custom_address(self, user: User):
        assert user.has_custom_address
        assert self.session.query(User).filter(User.has_custom_address).count() == 1

    def assert_no_custom_address(self, user: User):
        assert not user.has_custom_address
        assert self.session.query(User).filter(~User.has_custom_address).count() == 1

    def test_user_with_room(self):
        user = factories.UserFactory()
        self.assert_no_custom_address(user)

        user.address = factories.AddressFactory()
        self.assert_custom_address(user)

    def test_user_without_room(self):
        user = factories.UserWithoutRoomFactory()
        self.assert_no_custom_address(user)

        user.address = factories.AddressFactory()
        self.assert_no_custom_address(user)
