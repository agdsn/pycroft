#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t
from contextlib import contextmanager

import pytest
from sqlalchemy import inspect, update, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pycroft.helpers.user import login_hash
from pycroft.model.user import User
from pycroft.model.unix_account import UnixTombstone, UnixAccount
from tests import factories as f


L_HASH: bytes = login_hash("mylogin")


def test_login_hash_correct(session):
    user = f.UserFactory(login="mylogin")
    assert user.login_hash == L_HASH


class TestTombstoneConstraints:
    @staticmethod
    def test_tombstone_needs_login_hash_or_uid(session):
        session.add(UnixTombstone())
        with pytest.raises(IntegrityError, match="CheckViolation"):
            session.flush()

    @staticmethod
    @pytest.mark.parametrize(
        "tombstone_args",
        (
            [(None, 10000)] * 2,
            [(L_HASH, None)] * 2,
            [(None, 10000), (L_HASH, 10000)],
            [(L_HASH, 10000), (L_HASH, 10001)],
            [(L_HASH, 10000), (L_HASH, None)],
            [(None, None)],
        ),
    )
    def test_tombstone_uniqueness_violations(
        session: Session, tombstone_args: list[tuple[str, int]]
    ):
        session.add_all([UnixTombstone(login_hash=h, uid=u) for h, u in tombstone_args])
        with pytest.raises(IntegrityError):
            session.flush()

    @staticmethod
    def test_valid_tombstone_combinations(session: Session):
        session.add_all(
            UnixTombstone(login_hash=h, uid=uid)
            for h, uid in (
                (None, 10000),
                (L_HASH, None),
                (login_hash("login2"), 10001),
                (None, 20000),
            )
        )
        try:
            session.flush()
        except IntegrityError:
            pytest.fail("raised IntegrityError")


class TestUnixAccountUidFKey:
    @staticmethod
    @pytest.fixture(scope="class")
    def unix_account(class_session):
        account = f.UnixAccountFactory()
        class_session.flush()
        return account

    @staticmethod
    def test_unix_account_has_tombstone(unix_account):
        assert unix_account.tombstone

    @staticmethod
    def test_unix_account_deletion_keeps_tombstone(session, unix_account):
        tombstone = unix_account.tombstone
        session.delete(unix_account)
        session.flush()
        session.refresh(tombstone)
        assert inspect(tombstone).persistent

    @staticmethod
    def test_unix_account_uid_change_does_not_change_tombstone(session, unix_account):
        unix_account.uid += 1000
        session.add(unix_account)
        with pytest.raises(IntegrityError, match="ForeignKeyViolation"):
            session.flush()


class TestUserLoginHashFKey:
    # TODO test user add, modify, delete
    pass


@contextmanager
def constraints_deferred(session: Session, constraints: t.LiteralString = "all"):
    session.execute(text(f"set constraints {constraints} deferred"))
    yield
    session.execute(text(f"set constraints {constraints} immediate"))


class TestUserUnixAccountTombstoneConsistency:
    @pytest.fixture(scope="class")
    def user(self, class_session) -> User:
        user = f.UserFactory(with_unix_account=True)
        class_session.flush()
        return user

    def test_user_login_change_fails(self, session, user):
        # changing `user.login` does not work due to custom validator
        from sqlalchemy import update

        with pytest.raises(IntegrityError, match="user_login_hash_fkey"):
            stmt = (
                update(User)
                .where(User.id == user.id)
                .values(login=user.login + "_")
                .returning(User.login)
            )
            _new_login = session.scalars(stmt)

    def test_user_login_change_works_when_changing_tombstone(self, session, user):
        login_new = user.login + "_"
        tombstone = user.tombstone
        with constraints_deferred(session), session.begin_nested(), session.no_autoflush:
            session.execute(
                update(User).where(User.id == user.id).values(login=login_new).returning(User.login)
            )
            session.refresh(user)
            tombstone.login_hash = user.login_hash
            session.add(tombstone)

    def test_user_login_change_fails_when_creating_new_tombstone(self, session, user):
        login_new = user.login + "_"
        hash_hew: bytes = login_hash(login_new)
        MATCH_RE = "User tombstone.*and unix account tombstone.*differ"
        with (
            pytest.raises(IntegrityError, match=MATCH_RE),
            session.begin_nested(),
        ):
            session.add(UnixTombstone(uid=None, login_hash=hash_hew))
            session.execute(
                update(User).where(User.id == user.id).values(login=login_new).returning(User.login)
            )

    def test_ua_uid_change_fails(self, session, user):
        ua = user.unix_account
        with pytest.raises(IntegrityError, match="violates foreign key constraint"):
            ua.uid = ua.uid + 5
            session.add(ua)
            session.flush()

    def test_ua_uid_change_works_when_changing_tombstone(self, session, user):
        ua = user.unix_account
        ts = ua.tombstone
        new_uid = ua.uid + 5
        with constraints_deferred(session), session.begin_nested():
            ts.uid = new_uid
            ua.uid = new_uid
            session.add_all([ts, ua])
            session.flush()

    def test_ua_deletion(self, session, user):
        # Since a user exists, this should leave the user and the tombstone.
        uid = user.unix_account.uid
        with session.begin_nested():
            session.delete(user.unix_account)
        assert user.tombstone.uid == uid

    def test_user_deletion(self, session, user):
        ua = user.unix_account
        with session.begin_nested():
            session.delete(user)
        assert inspect(user).deleted, "user did not get deleted"
        assert inspect(ua).deleted, "unix_account did not get deleted"

    def test_user_change_unix_account(self, session, user):
        with pytest.raises(IntegrityError), session.begin_nested():
            ua = f.UnixAccountFactory()
            user.unix_account = ua
            session.add(user)


class TestUserNoUnixAccount:
    @pytest.fixture(scope="class")
    def user(self, class_session) -> User:
        user = f.UserFactory()
        class_session.flush()
        return user

    def test_add_new_unix_account_to_user(self, session, user):
        # should also not throw an error.
        # not sure why we care about this use case,
        # but this should be possible in principle (think external users).
        with session.begin_nested():
            ua = f.UnixAccountFactory()
            user.unix_account = ua
            session.add(user)


class TestUnixAccountNoUser:
    @pytest.fixture(scope="class")
    def unix_account(self, class_session) -> UnixAccount:
        ua = f.UnixAccountFactory()
        class_session.flush()
        return ua

    def test_create_user_with_existing_unix_account(self, session, unix_account):
        # this should not throw an error,
        # because "UA then User" is the usual order of operations when creating a new user.
        ua = unix_account
        try:
            with session.begin_nested():
                session.add(f.UserFactory(unix_account=ua))
        except IntegrityError:
            pytest.fail("Creating user raised IntegrityError.")


class TestTombstoneLifeCycle:
    @pytest.fixture(scope="class")
    def tombstone(self, class_session):
        tombstone = UnixTombstone(uid=999, login_hash=L_HASH)
        class_session.add(tombstone)
        return tombstone

    def test_cannot_set_uid_null(self, session, tombstone):
        with pytest.raises(IntegrityError), session.begin_nested():
            session.execute(
                update(UnixTombstone).values(uid=None).where(UnixTombstone.uid == tombstone.uid)
            )

    def test_cannot_set_login_hash_null(self, session, tombstone):
        with pytest.raises(IntegrityError), session.begin_nested():
            session.execute(
                update(UnixTombstone)
                .values(login_hash=None)
                .where(UnixTombstone.uid == tombstone.uid)
            )
