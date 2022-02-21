# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

import pytest

from pycroft.helpers.interval import single, closedopen
from pycroft.helpers.user import generate_password, hash_password
from pycroft.model.user import IllegalLoginError, Membership, User, UnixAccount
from tests import factories


class Test_User_Passwords:
    @pytest.fixture(scope='class')
    def user(self, class_session):
        return factories.UserFactory()

    def test_password_hash_validator(self, user, session):
        password = generate_password(4)
        pw_hash = hash_password(password)

        user.passwd_hash = pw_hash
        session.flush()

        with session.begin_nested(), \
            pytest.raises(AssertionError,
                          match="A password-hash with less than 9 chars is not correct!"):
            user.passwd_hash = password
            session.flush()

        with pytest.raises(AssertionError, match="Cannot clear the password hash!"):
            user.passwd_hash = None
            session.flush()

    @pytest.mark.slow
    @pytest.mark.timeout(15)
    def test_set_and_verify_password(self, user, session):
        password = generate_password(4)
        user.password = password
        session.flush()

        assert user.check_password(password)
        assert User.verify_and_get(user.login, password) == user

        assert User.verify_and_get(user.login, password + "_wrong") is None

        # TODO reduce set of examples, this is excessive.
        # Also, why do we depend on `generate_password` instead of testing it separately?
        # All of this is very unperformant with little benefit.
        for length in range(4, 10):
            for cnt in range(1, 3):
                pw = generate_password(length)
                if pw == password:
                    continue
                assert not user.check_password(pw)
                assert User.verify_and_get(user.login, pw) is None


class Test_User_Login:
    @pytest.fixture(scope='class')
    def user(self, class_session):
        """A persistent user (i.e., in the db)"""
        return factories.UserFactory()

    @pytest.fixture(scope='class')
    def transient_user(self):
        """A user not yet in the db"""
        return factories.UserFactory.build()

    @pytest.mark.parametrize('login', [
        # simple valid logins
        "abcdefg", "a-b", "a3b", "a.2b", "a33", "a-4",
        *("a" * l for l in range(2, 23)),
    ])
    def test_good_logins(self, transient_user, login):
        transient_user.login = login

    @pytest.mark.parametrize('login', [
        # invalid logins (charset)
        "123", "ABC", "3bc", "_ab", "ab_", "3b_", "_b3", "&&",
        "a_b", "a_2b", "a_4", "-ab", "ab-", ".ab", "ab.",
        # blocked logins
        "abuse", "admin", "administrator", "autoconfig",
        "broadcasthost", "root", "daemon", "bin", "sys", "sync",
        "games", "man", "hostmaster", "imap", "info", "is",
        "isatap", "it", "localdomain", "localhost",
        "lp", "mail", "mailer-daemon", "news", "uucp", "proxy",
        "majordom", "marketing", "mis", "noc", "website", "api",
        "noreply", "no-reply", "pop", "pop3",
        "postmaster",
        "postgres", "sales", "smtp", "ssladmin", "status",
        "ssladministrator", "sslwebmaster", "support",
        "sysadmin", "usenet", "webmaster", "wpad", "www",
        "wwwadmin", "backup", "msql", "operator", "user",
        "ftp", "ftpadmin", "guest", "bb", "nobody", "www-data",
        "bacula", "contact", "email", "privacy", "anonymous",
        "web", "git", "username", "log", "login", "help", "name",
        # logins with bad lengt
        "a", "a" * 23, "a" * 24
    ])
    def test_bad_logins(self, transient_user, login):
        with pytest.raises(IllegalLoginError):
            transient_user.login = login

    def test_login_cannot_be_changed(self, session, user):
        with pytest.raises(AssertionError,
                           match="user already in the database - cannot change login anymore!"):
            user.login = "abc"

    def test_user_login_case_insensitive(self, session, user):
        password = 'password'
        assert User.verify_and_get(user.login, password) == user
        # Verification of login name should be case insensitive
        assert User.verify_and_get(user.login.upper(), password) == user


class TestUnixAccounts:
    @pytest.fixture(scope='class')
    def ldap_user(self, class_session):
        return factories.UserFactory(with_unix_account=True)

    @pytest.fixture(scope='class')
    def dummy_user(self, class_session):
        return factories.UserFactory()

    @pytest.fixture(scope='class')
    def custom_account(self, class_session):
        return factories.UnixAccountFactory(gid=27)

    @pytest.fixture(scope='class')
    def dummy_account(self, class_session):
        return factories.UnixAccountFactory()

    @pytest.fixture(autouse=True)
    def flush(self, session):
        return session.flush()

    def test_correct_default_values(self, dummy_account):
        assert dummy_account.gid == 100
        assert dummy_account.uid >= 1000
        assert dummy_account.login_shell

    def test_custom_ids_set(self, custom_account):
        assert custom_account.gid == 27

    def test_account_reference(self, ldap_user, dummy_user):
        assert isinstance(ldap_user.unix_account, UnixAccount)
        assert ldap_user.unix_account.home_directory.startswith('/home/')
        assert dummy_user.unix_account is None


class TestActiveHybridMethods:
    @pytest.fixture(scope='class')
    def user(self, class_session):
        return factories.UserFactory()

    @pytest.fixture(scope='class')
    def property_group(self, class_session):
        return factories.PropertyGroupFactory()

    @pytest.fixture
    def add_membership(self, session, utcnow, user):
        def _add_membership(group):
            with session.begin_nested():
                m = Membership(user=user, group=group, active_during=closedopen(utcnow, None))
                session.add(m)
            return m
        return _add_membership

    def test_active_memberships(self, session, utcnow, user, property_group, add_membership):
        assert user.active_memberships() == []
        assert user.current_memberships == []

        m = add_membership(property_group)
        session.refresh(user)

        assert user.active_memberships() == [m]
        assert user.current_memberships == [m]

        when = single(utcnow - timedelta(hours=1))
        assert user.active_memberships(when) == []
        when = single(utcnow + timedelta(hours=1))
        assert user.active_memberships(when) == [m]

    @pytest.fixture
    def create_active_memberships_query(self, user, session):
        def _create_active_memberships_query(when=None):
            return session.scalars(User.active_memberships(when).where(User.id == user.id))
        return _create_active_memberships_query

    def test_active_memberships_expression(
        self, session, utcnow, property_group, add_membership, create_active_memberships_query,
    ):
        query = create_active_memberships_query()
        assert query.all() == []
        m = add_membership(property_group)
        query = create_active_memberships_query()
        assert query.all() == [m]
        when = single(utcnow - timedelta(hours=1))
        query = create_active_memberships_query(when)
        assert query.all() == []
        when = single(utcnow + timedelta(hours=1))
        query = create_active_memberships_query(when)
        assert query.all() == [m]

    def test_active_property_groups(self, session, utcnow, user, property_group, add_membership):
        assert user.active_property_groups() == []
        add_membership(property_group)
        assert user.active_property_groups() == [property_group]
        when = single(utcnow - timedelta(hours=1))
        assert user.active_property_groups(when) == []
        when = single(utcnow + timedelta(hours=1))
        assert user.active_property_groups(when) == [property_group]

    @pytest.fixture
    def create_active_property_groups_query(self, user, session):
        def _create_active_property_groups_query(when=None):
            return session.scalars(User.active_property_groups(when).where(User.id == user.id))
        return _create_active_property_groups_query

    def test_active_property_groups_expression(
        self, session, utcnow, user, property_group,
        add_membership, create_active_property_groups_query,
    ):
        query = create_active_property_groups_query()
        assert query.all() == []

        add_membership(property_group)

        query = create_active_property_groups_query()
        assert query.all() == [property_group]
        when = single(utcnow - timedelta(hours=1))
        query = create_active_property_groups_query(when)
        assert query.all() == []
        when = single(utcnow + timedelta(hours=1))
        query = create_active_property_groups_query(when)
        assert query.all() == [property_group]


class Test_has_property:
    GRANTED_NAME = 'granted'
    DENIED_NAME = 'denied'

    @pytest.fixture(scope='class')
    def user(self, class_session):
        return factories.UserFactory()

    @pytest.fixture(scope='class', autouse=True)
    def membership(self, class_session, user):
        group = factories.PropertyGroupFactory(granted={self.GRANTED_NAME},
                                               denied={self.DENIED_NAME})
        return factories.MembershipFactory(group=group, user=user, includes_today=True)

    @pytest.mark.parametrize('property, should_exist', [
        (GRANTED_NAME, True),
        (DENIED_NAME, False),
        ('unused', False),
    ])
    def test_positive_test(self, session, user, property, should_exist):
        assert user.has_property(property) == should_exist

    @pytest.mark.parametrize('timestamp_getter, should_exist', [
        (lambda i: i.begin - timedelta(seconds=1), False),

        (lambda i: i.begin, True),
        (lambda i: i.begin + timedelta(seconds=1), True),
        (lambda i: i.end - timedelta(seconds=1), True),

        (lambda i: i.end, False),
        (lambda i: i.end + timedelta(1), False),
        (lambda i: i.end + timedelta(2), False),
    ])
    def test_has_property_interval(self, session, user, membership,
                                   timestamp_getter, should_exist):
        timestamp = timestamp_getter(membership.active_during)
        assert user.has_property(self.GRANTED_NAME, timestamp) == should_exist


class TestUserAddress:
    @staticmethod
    def assert_custom_address(session, user: User):
        assert user.has_custom_address
        assert session.query(User).filter(User.has_custom_address).count() == 1

    @staticmethod
    def assert_no_custom_address(session, user: User):
        assert not user.has_custom_address
        assert session.query(User).filter(~User.has_custom_address).count() == 1

    def test_user_with_room(self, session):
        user = factories.UserFactory()
        self.assert_no_custom_address(session, user)

        user.address = factories.AddressFactory()
        self.assert_custom_address(session, user)

    def test_user_without_room(self, session):
        user = factories.UserFactory(without_room=True)
        self.assert_no_custom_address(session, user)

        user.address = factories.AddressFactory()
        self.assert_no_custom_address(session, user)
