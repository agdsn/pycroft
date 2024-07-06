#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t
from contextlib import contextmanager
from hashlib import sha512

import pytest
from sqlalchemy import inspect, update, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pycroft.model.user import UnixTombstone, User
from tests import factories as f


L_HASH = sha512(b"login").hexdigest()


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
                (sha512(b"login2").hexdigest(), 10001),
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
        hash_hew: bytes = sha512(login_new.encode()).digest()
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
        pytest.fail("TODO")

    def test_ua_uid_change_works_when_changing_tombstone(self, session, user):
        pytest.fail("TODO")

    def test_ua_deletion(self, session, user):
        pytest.fail("TODO")

    def test_user_deletion(self, session, user):
        pytest.fail("TODO")


class TestTombstoneLifeCycle:
    # TODO: FIXTURE: isolated unix tombstone, nothing else existing

    def test_cannot_set_uid_null(self, session):
        pytest.fail("TODO")

    def test_cannot_set_login_hash_null(self, session):
        pytest.fail("TODO")
