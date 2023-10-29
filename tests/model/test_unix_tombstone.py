#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from hashlib import sha512

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pycroft.model.user import UnixTombstone
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


class TestUserUnixAccountTombstoneConsistency:
    # TODO test that modifications on user/unix_account
    #  (e.g. creation, attr modification)
    #  throw an error if both entities point to different tombstones

    # TODO test: adding a unix account pointing to user w/ tombstone w/ different uid
    #  throws an error
    pass
