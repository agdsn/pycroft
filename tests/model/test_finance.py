#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from datetime import datetime

import pytest
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError

from pycroft.model.finance import Transaction, IllegalTransactionError, Split, BankAccountActivity
from tests.factories import AccountFactory, UserFactory
from tests.factories.finance import BankAccountFactory


@pytest.fixture
def author(session):
    return UserFactory()


@pytest.fixture
def asset_account(session):
    return AccountFactory(type='ASSET')


@pytest.fixture
def revenue_account(session):
    return AccountFactory(type='REVENUE')


@pytest.fixture
def liability_account(session):
    return AccountFactory(type='LIABILITY')


@pytest.fixture(name='t')
def transaction(author):
    return Transaction(description='Transaction', author=author)


def create_split(t, account, amount):
    return Split(amount=amount, account=account, transaction=t)


def test_empty_t(session, t):
    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            session.add(t)


def test_fail_on_unbalance(session, t, asset_account):
    split = create_split(t, asset_account, 100)
    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            session.add_all([t, split])


def test_insert_balanced(session, t, asset_account, revenue_account):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, revenue_account, -100)
    try:
        with session.begin_nested():
            session.add_all([s1, s2])
    except IllegalTransactionError:
        pytest.fail("Threw illegalterror")


def test_delete_cascade_transaction_to_splits(
    session, t, asset_account, revenue_account
):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, revenue_account, -100)
    with session.begin_nested():
        session.add_all([t, s1, s2])
    with session.begin_nested():
        session.delete(t)  # should delete associated splits
    assert session.scalars(select(func.count(Split.id))).one() == 0


def test_fail_on_self_transaction(session, t, asset_account):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, asset_account, -100)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2])


def test_fail_on_multiple_split_same_account(
    session, t, asset_account, revenue_account
):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, revenue_account, -50)
    s3 = create_split(t, revenue_account, -50)

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2, s3])


@pytest.fixture
def balanced_splits(session, t, asset_account, revenue_account):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, revenue_account, -100)
    with session.begin_nested():
        session.add_all([t, s1, s2])
    return s1, s2


def test_unbalance_with_insert(
    session, t, balanced_splits, liability_account
):
    s3 = create_split(t, liability_account, 50)

    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            session.add(s3)


def test_unbalance_with_update(session, balanced_splits):
    _, s2 = balanced_splits

    with pytest.raises(IllegalTransactionError):
        with session.begin_nested():
            s2.amount = -50


def test_unbbalance_with_delete(session, t, balanced_splits):
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


@pytest.fixture(scope='session')
def utcnow():
    return datetime.utcnow()


@pytest.fixture
def create_activity(bank_account, utcnow):
    def _create(amount):
        # TODO replace by factory
        return BankAccountActivity(
            bank_account=bank_account,
            reference='Reference',
            other_name='John Doe',
            other_account_number='0123456789',
            other_routing_number='01245',
            amount=amount,
            imported_at=utcnow,
            posted_on=utcnow.date(),
            valid_on=utcnow.date(),
        )

    return _create


def test_correct(session, create_activity, bank_account, t, asset_account):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, bank_account.account, -100)
    a = create_activity(-10)
    a.split = s2
    with session.begin_nested():
        session.add_all([t, s1, s2, a])


def test_wrong_split_amount(
    session, immediate_trigger,
    create_activity, bank_account, t, asset_account
):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, bank_account.account, -100)
    a = create_activity(-50)
    a.split = s2

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2, a])


def test_wrong_split_account(
    session, immediate_trigger,
    create_activity, revenue_account, t, asset_account
):
    s1 = create_split(t, asset_account, 100)
    s2 = create_split(t, revenue_account, -100)
    a = create_activity(-100)
    a.split = s2

    with pytest.raises(IntegrityError):
        with session.begin_nested():
            session.add_all([t, s1, s2, a])
