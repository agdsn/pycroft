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
from itertools import zip_longest

from sqlalchemy import func
from sqlalchemy import select
from sqlalchemy.orm import Session

from pycroft.model.finance import (
    BankAccountActivity,
    Split,
    Transaction,
)
from pycroft.model.user import User
from .matching import match_activities
from .membership_fee import (
    get_membership_fee_for_date,
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


def import_newer_than_days(session: Session, days: int) -> bool:
    # TODO properly test this
    return session.scalar(
        select(
            func.max(BankAccountActivity.imported_at)
            >= func.current_timestamp() - timedelta(days=days)
        ),
    )
