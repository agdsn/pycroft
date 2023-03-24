#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import typing as t
from datetime import timedelta, date
from decimal import Decimal

from mt940.models import Transaction as MT940Transaction
from sqlalchemy import select, func, Select, text
from sqlalchemy.orm import contains_eager

from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.logging import log_event
from pycroft.model import session
from pycroft.model.base import ModelBase
from pycroft.model.finance import (
    Transaction,
    Account,
    Split,
    BankAccountActivity,
    BankAccount,
)
from pycroft.model.session import with_transaction
from pycroft.model.user import User
from pycroft.model.utils import row_exists


@with_transaction
def simple_transaction(
    description: str,
    debit_account: Account,
    credit_account: Account,
    amount: Decimal,
    author: User,
    valid_on: date | None = None,
    confirmed: bool = True,
) -> Transaction:
    """Posts a simple transaction.

    A simple transaction is a transaction that consists of exactly two splits,
    where one account is debited and another different account is credited with
    the same amount.
    The current system date will be used as transaction date, an optional valid
    date may be specified.

    :param description: Description
    :param debit_account: Debit (germ. Soll) account.
    :param credit_account: Credit (germ. Haben) account
    :param amount: Amount in Eurocents
    :param author: User who created the transaction
    :param valid_on: Date, when the transaction should be valid. Current database date, if omitted.
    :param confirmed: If transaction should be created as confirmed
    """
    if valid_on is None:
        valid_on = session.utcnow().date()
    new_transaction = Transaction(
        description=description, author=author, valid_on=valid_on, confirmed=confirmed
    )
    new_debit_split = Split(
        amount=-amount, account=debit_account, transaction=new_transaction
    )
    new_credit_split = Split(
        amount=amount, account=credit_account, transaction=new_transaction
    )
    session.session.add_all([new_transaction, new_debit_split, new_credit_split])
    return new_transaction


@with_transaction
def complex_transaction(
    description: str,
    author: User,
    splits: t.Iterable[tuple[Account, Decimal]],
    valid_on: date | None = None,
    confirmed: bool = True,
) -> Transaction:
    if valid_on is None:
        valid_on = session.utcnow().date()
    objects: list[ModelBase] = []
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_on=valid_on,
        confirmed=confirmed,
    )
    objects.append(new_transaction)
    objects.extend(
        Split(amount=amount, account=account, transaction=new_transaction)
        for (account, amount) in splits
    )
    session.session.add_all(objects)
    return new_transaction


@with_transaction
def transaction_delete(transaction: Transaction, processor: User) -> None:
    if transaction.confirmed:
        raise ValueError("transaction already confirmed")

    session.session.delete(transaction)

    message = deferred_gettext("Deleted transaction {}.").format(transaction.id)
    log_event(message.to_json(), author=processor)


@with_transaction
def transaction_confirm(transaction: Transaction, processor: User) -> None:
    if transaction.confirmed:
        raise ValueError("transaction already confirmed")

    transaction.confirmed = True

    message = deferred_gettext("Confirmed transaction {}.").format(transaction.id)
    log_event(message.to_json(), author=processor)


@with_transaction
def transaction_confirm_all(processor: User) -> None:
    # Confirm all transactions older than one hour that are not confirmed yet
    transactions = session.session.scalars(
        select(Transaction)
        .filter_by(confirmed=False)
        .filter(Transaction.posted_at < func.current_timestamp() - timedelta(hours=1))
    )
    for transaction in transactions:
        transaction_confirm(transaction, processor)


def build_transactions_query(
    account: Account,
    search: str | None = None,
    sort_by: str = "valid_on",
    sort_order: str | None = None,
    offset: int | None = None,
    limit: int | None = None,
    positive: bool | None = None,
    eagerload: bool = False,
) -> Select[tuple[Split]]:
    """Build a query returning the Splits for a finance account

    :param account: The finance Account to filter by
    :param search: The string to be included, insensitive
    :param sort_by: The column to sort by.  Must be a column of
        :class:`Transaction` or :class:`Split`.
    :param sort_order: Trigger descending sort order if the value
        is ``'desc'``.  See also the effect of :attr:`positive`.
    :param offset:
    :param limit:
    :param positive: if positive is set to ``True``, only get
        splits with amount ≥ 0, and amount < 0 if ``False``.  In the
        latter case, the effect of the :attr:`sort_order` parameter is
        being reversed.
    :param eagerload: Eagerly load involved transactions.

    :returns: The prepared SQLAlchemy query
    """
    stmt = select(Split).join(Transaction).filter(Split.account == account)

    # see #562
    if not (
        sort_by in Transaction.__table__.columns or sort_by in Split.__table__.columns
    ):
        sort_by = "valid_on"

    descending = (sort_order == "desc") ^ (positive is False)
    ordering = sort_by + " desc" if descending else sort_by
    if search:
        stmt = stmt.filter(Transaction.description.ilike(f"%{search}%"))

    if positive is not None:
        if positive:
            stmt = stmt.filter(Split.amount >= 0)
        else:
            stmt = stmt.filter(Split.amount < 0)

    stmt = stmt.order_by(text(ordering)).offset(offset).limit(limit)

    if eagerload:
        stmt = stmt.options(contains_eager(Split.transaction))

    return stmt


def _similar_activity_stmt(activity: BankAccountActivity) -> Select:
    return (
        select()
        .select_from(BankAccountActivity)
        .filter_by(
            bank_account_id=activity.bank_account_id,
            amount=activity.amount,
            reference=activity.reference,
            other_account_number=activity.other_account_number,
            other_routing_number=activity.other_routing_number,
            other_name=activity.other_name,
            posted_on=activity.posted_on,
            valid_on=activity.valid_on,
        )
    )


class ImportedTransactions(t.NamedTuple):
    new: list[BankAccountActivity]
    old: list[BankAccountActivity]
    doubtful: list[BankAccountActivity]


def process_transactions(
    bank_account: BankAccount,
    statement: t.Iterable[MT940Transaction],
) -> ImportedTransactions:
    imported = ImportedTransactions([], [], [])

    for transaction in statement:
        iban: str = transaction.data.get("applicant_iban") or ""
        bic: str = transaction.data.get("applicant_bin") or ""
        other_name: str = transaction.data.get("applicant_name") or ""
        purpose = transaction.data.get("purpose") or ""
        if (
            "end_to_end_reference" in transaction.data
            and transaction.data["end_to_end_reference"] is not None
        ):
            purpose = purpose + " EREF+" + transaction.data["end_to_end_reference"]

        new_activity = BankAccountActivity(
            bank_account_id=bank_account.id,
            amount=transaction.data["amount"].amount,
            reference=purpose,
            other_account_number=iban,
            other_routing_number=bic,
            other_name=other_name,
            imported_at=session.utcnow(),
            posted_on=transaction.data["guessed_entry_date"],
            valid_on=transaction.data["date"],
        )
        if new_activity.posted_on >= date.today():
            imported.doubtful.append(new_activity)
        elif row_exists(session.session, _similar_activity_stmt(new_activity)):
            imported.new.append(new_activity)
        else:
            imported.old.append(new_activity)

    return imported
