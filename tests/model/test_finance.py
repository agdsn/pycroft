#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from functools import partial

import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError, DataError

from pycroft.model.finance import Transaction, IllegalTransactionError, Split, Account
from tests.factories import AccountFactory, UserFactory
from tests.factories.finance import BankAccountFactory, BankAccountActivityFactory


@pytest.fixture
def author(session):
    return UserFactory()


@pytest.fixture(scope='module')
def asset_account(module_session):
    return AccountFactory(type='ASSET')


@pytest.fixture(scope='module')
def revenue_account(module_session):
    return AccountFactory(type='REVENUE')


@pytest.fixture(scope='module')
def liability_account(module_session):
    return AccountFactory(type='LIABILITY')


@pytest.fixture(name='t')
def transaction(author):
    return Transaction(description='Transaction', author=author)


def build_split(t, account, amount):
    return Split(amount=amount, account=account, transaction=t)


def test_empty_t(session, t):
    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            session.add(t)


def test_fail_on_unbalance(session, t, asset_account):
    split = build_split(t, asset_account, 100)
    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            session.add_all([t, split])


def test_insert_balanced(session, t, asset_account, revenue_account):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, revenue_account, -100)
    try:
        with session.begin_nested():
            session.add_all([s1, s2])
    except IllegalTransactionError:
        pytest.fail("Threw illegalterror")


def test_delete_cascade_transaction_to_splits(
    session, t, asset_account, revenue_account
):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, revenue_account, -100)
    with session.begin_nested():
        session.add_all([t, s1, s2])
    with session.begin_nested():
        session.delete(t)  # should delete associated splits
    assert session.scalars(select(func.count(Split.id))).one() == 0


def test_fail_on_self_transaction(session, t, asset_account):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, asset_account, -100)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2])


def test_fail_on_multiple_split_same_account(
    session, t, asset_account, revenue_account
):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, revenue_account, -50)
    s3 = build_split(t, revenue_account, -50)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2, s3])


@pytest.fixture
def balanced_splits(session, t, asset_account, revenue_account):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, revenue_account, -100)
    with session.begin_nested():
        session.add_all([t, s1, s2])
    return s1, s2


def test_unbalance_with_insert(
    session, t, balanced_splits, liability_account
):
    with pytest.raises(IllegalTransactionError), session.begin_nested():
        session.add(build_split(t, liability_account, 50))


def test_unbalance_with_update(session, balanced_splits):
    _, s2 = balanced_splits

    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            s2.amount = -50


def test_unbalance_with_delete(session, t, balanced_splits):
    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            t.splits.pop()


@pytest.fixture(name='immediate_trigger')
def immediate_activity_matches_split_trigger(session):
    session.execute(text(
        "SET CONSTRAINTS bank_account_activity_matches_referenced_split_trigger"
        " IMMEDIATE"
    ))
    yield None
    session.execute(text(
        "SET CONSTRAINTS bank_account_activity_matches_referenced_split_trigger"
        " DEFERRED"
    ))


@pytest.fixture
def bank_account():
    return BankAccountFactory()


@pytest.fixture
def build_activity(bank_account, utcnow):
    return partial(
        BankAccountActivityFactory.build,
        bank_account=bank_account, imported_at=utcnow,
    )


def test_correct(session, build_activity, bank_account, t, asset_account):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, bank_account.account, -100)
    a = build_activity(amount=-10, split=s2)
    session.add_all([t, s1, s2, a])
    session.flush()


def test_wrong_split_amount(
    session, immediate_trigger,
    build_activity, bank_account, t, asset_account
):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, bank_account.account, -100)
    a = build_activity(amount=-50, split=s2)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2, a])


def test_wrong_split_account(
    session, immediate_trigger,
    build_activity, revenue_account, t, asset_account
):
    s1 = build_split(t, asset_account, 100)
    s2 = build_split(t, revenue_account, -100)
    a = build_activity(amount=-100, split=s2)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2, a])


def test_create_account_type(session):
    with session.begin_nested():
        session.add(Account(name="foo", type="USER_ASSET"))


def test_create_account_bad_type(session):
    with pytest.raises(DataError), session.begin_nested():
        session.add(Account(name="foo", type="BadType"))
