# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.finance
~~~~~~~~~~~~~~~~~~~
"""
import typing
import typing as t
from datetime import datetime, timedelta
from itertools import zip_longest, groupby

from sqlalchemy import func, and_
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from pycroft.model.finance import (
    Account,
    BankAccountActivity,
    Split,
    Transaction,
    BankAccount,
    MT940Error,
    AccountType,
)
from pycroft.model.user import User
from .matching import match_activities
from .membership_fee import (
    get_membership_fee_for_date,
    get_last_membership_fee,
    get_last_applied_membership_fee,
    estimate_balance,
    post_transactions_for_membership_fee,
    membership_fee_description,
)
from .payment_in_default import (
    end_payment_in_default_memberships,
    get_last_payment_in_default_membership,
    get_negative_members,
    get_users_with_payment_in_default,
    take_actions_for_payment_in_default_users,
    get_pid_csv,
    filter_active_members_from_users_with_pid,
)
from .retransfer import (
    attribute_activities_as_returned,
    generate_activities_return_sepaxml,
    get_activities_to_return,
)
from .transaction_crud import (
    simple_transaction,
    complex_transaction,
    transaction_delete,
    transaction_confirm,
    transaction_confirm_all,
    build_transactions_query,
    process_transactions,
    ImportedTransactions,
)


def user_has_paid(user: User) -> bool:
    return t.cast(int, user.account.balance) <= 0


def get_typed_splits(
    splits: typing.Sequence[Split],
) -> typing.Iterable[tuple[Split, Split]]:
    splits = sorted(splits, key=lambda s: s.transaction.posted_at, reverse=True)
    return zip_longest(
        (s for s in splits if s.amount >= 0),
        (s for s in splits if s.amount < 0),
    )


def get_transaction_type(transaction: Transaction) -> tuple[str, str] | None:
    credited_types = {
        split.account.type for split in transaction.splits if split.amount > 0
    }
    debited_types = {
        split.account.type for split in transaction.splits if split.amount < 0
    }
    if len(credited_types) == len(debited_types) == 1:
        [cred_type] = credited_types
        [deb_type] = debited_types
        return cred_type, deb_type
    return None


def get_last_import_date(session: Session) -> datetime | None:
    date: datetime | None = session.scalars(
        select(func.max(BankAccountActivity.imported_at))
    ).first()
    return date


def import_newer_than_days(session: Session, days: int) -> bool | None:
    # TODO properly test this
    return session.scalar(
        select(
            func.max(BankAccountActivity.imported_at)
            >= func.current_timestamp() - timedelta(days=days)
        )
    )


def get_system_accounts(session: Session) -> list[Account]:
    """Return all accounts which neither belong to a user nor are user assets"""
    # TODO use session.execute(select(…))
    return (
        Account.q.outerjoin(User)
        .filter(and_(User.account_id.is_(None), Account.type != "USER_ASSET"))
        .all()
    )


def get_accounts_by_type(
    session: Session,
) -> dict[AccountType | t.Literal["LEGACY"], list[Account]]:
    def _key(a: Account) -> AccountType:
        return a.type

    accounts_by_type: dict[AccountType | t.Literal["LEGACY"], list[Account]] = {
        type: list(acc)
        for type, acc in groupby(
            Account.q.filter_by(legacy=False)
            .outerjoin(User)
            .filter(User.id.is_(None))
            .order_by(Account.type)
            .all(),
            _key,
        )
    }

    accounts_by_type["LEGACY"] = Account.q.filter_by(legacy=True).all()
    return accounts_by_type


def get_all_bank_accounts(session: Session) -> list[BankAccount]:
    return BankAccount.q.all()


def get_unassigned_bank_account_activities(
    session: Session,
) -> list[BankAccountActivity]:
    return (
        BankAccountActivity.q.options(joinedload(BankAccountActivity.bank_account))
        .filter(BankAccountActivity.transaction_id.is_(None))
        .all()
    )


def get_all_mt940_errors(session: Session) -> list[MT940Error]:
    return MT940Error.q.all()
