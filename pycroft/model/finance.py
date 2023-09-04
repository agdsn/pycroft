# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.finance
~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations
import datetime
import typing as t
from datetime import timedelta, date
from decimal import Decimal
from math import fabs

from sqlalchemy import ForeignKey, event, func, select, Enum, ColumnElement, Select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, object_session, Mapped, mapped_column
from sqlalchemy.schema import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.types import String, Text

from pycroft.helpers.i18n import gettext
from pycroft.helpers.interval import closed
from pycroft.model import ddl
from pycroft.model.types import Money
from .base import IntegerIdModel
from .exc import PycroftModelException
from .type_aliases import str127, str255, datetime_tz_onupdate
from ..helpers import utc
from ..helpers.utc import DateTimeTz

manager = ddl.DDLManager()

if t.TYPE_CHECKING:
    # FKeys
    # backrefs
    from .facilities import Building
    from .user import User


class MembershipFee(IntegerIdModel):
    name: Mapped[str]
    regular_fee: Mapped[int] = mapped_column(Money, CheckConstraint("regular_fee >= 0"))

    # Timedelta after which a member has to pay
    booking_begin: Mapped[timedelta]

    # Timedelta until which a member has to pay
    booking_end: Mapped[timedelta]

    # Timedelta after which members are being charged a late fee for not paying
    # in time + will be added to a group with "payment_in_default" property
    payment_deadline: Mapped[timedelta]

    # Timedelta after which the membership will be cancelled
    payment_deadline_final: Mapped[timedelta]

    begins_on: Mapped[date]
    ends_on: Mapped[date]

    def __contains__(self, date):
        return date in closed(self.begins_on, self.ends_on)

    __table_args__ = (
        CheckConstraint('begins_on <= ends_on'),
    )


class Semester(IntegerIdModel):
    name: Mapped[str]
    registration_fee: Mapped[int] = mapped_column(
        Money,
        CheckConstraint('registration_fee >= 0')
    )
    regular_semester_fee: Mapped[int] = mapped_column(
        Money,
        CheckConstraint('regular_semester_fee >= 0'),
    )
    reduced_semester_fee: Mapped[int] = mapped_column(
        Money,
        CheckConstraint('reduced_semester_fee >= 0'),
    )
    late_fee: Mapped[int] = mapped_column(Money, CheckConstraint('late_fee >= 0'))
    # Timedelta a person has to be member in a semester to be charged any
    # semester fee at all(grace period)
    grace_period: Mapped[timedelta]
    # Timedelta a member has to be present (i.e. not away although being member)
    # in a semester to be charged the full fee
    reduced_semester_fee_threshold: Mapped[timedelta]
    # Timedelta after which members are being charged a late fee for not paying
    # in time
    payment_deadline: Mapped[timedelta]
    # Amount of outstanding debt a member can have without being charged a late
    # fee
    allowed_overdraft: Mapped[int] = mapped_column(
        Money,
        CheckConstraint('allowed_overdraft >= 0'),
    )
    begins_on: Mapped[date]
    ends_on: Mapped[date]

    def __contains__(self, date):
        return date in closed(self.begins_on, self.ends_on)

    __table_args__ = (
        CheckConstraint('begins_on < ends_on'),
    )


AccountType = t.Literal[
    "ASSET",  # Aktivkonto
    "USER_ASSET",  # Aktivkonto for users
    "BANK_ASSET",  # Aktivkonto for bank accounts
    "LIABILITY",  # Passivkonto
    "EXPENSE",  # Aufwandskonto
    "REVENUE",  # Ertragskonto
]

class Account(IntegerIdModel):
    name: Mapped[str127]
    # noinspection PyUnresolvedReferences
    type: Mapped[AccountType] = mapped_column(
        Enum(*AccountType.__args__, name="account_type"),
    )
    legacy: Mapped[bool] = mapped_column(default=False)

    # backrefs
    splits: Mapped[list[Split]] = relationship(viewonly=True, back_populates="account")
    user: Mapped[User | None] = relationship(viewonly=True, back_populates="account")
    building: Mapped[Building | None] = relationship(
        back_populates="fee_account", uselist=False
    )
    patterns: Mapped[list[AccountPattern]] = relationship(back_populates="account")
    transactions: Mapped[list[Transaction]] = relationship(
        secondary="split", back_populates="accounts", viewonly=True
    )
    # /backrefs

    @hybrid_property
    def _balance(self) -> int:
        return sum(s.amount for s in self.splits)

    @_balance.expression
    def balance(cls) -> ColumnElement[int]:
        return select(func.coalesce(func.sum(Split.amount), 0))\
            .where(Split.account_id == cls.id)\
            .label("balance")

    @hybrid_property
    def in_default_days(self):
        first_overdue = False
        split_sum = 0

        splits = Split.q.filter(Split.account_id == self.id) \
                        .join(Transaction) \
                        .order_by(Transaction.valid_on)

        for split in splits:
            split_sum += split.amount

            if split_sum > 0:
                if not first_overdue:
                    first_overdue = split.transaction.valid_on
            else:
                first_overdue = False

        if not first_overdue:
            return 0

        return fabs((first_overdue - datetime.date.today()).days)


manager.add_function(
    Account.__table__,
    ddl.Function(
        'account_is_type', ['integer', 'account_type'], 'boolean',
        "SELECT type = $2 FROM account WHERE id = $1 ",
        volatility='stable', strict=True,
    )
)


class AccountPattern(IntegerIdModel):
    pattern: Mapped[str]
    account_id: Mapped[int] = mapped_column(ForeignKey(Account.id, ondelete="CASCADE"))
    account: Mapped[Account] = relationship(Account, back_populates="patterns")


class Transaction(IntegerIdModel):
    description: Mapped[str] = mapped_column(Text())
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL", onupdate="CASCADE")
    )
    author: Mapped[User | None] = relationship("User")
    # workaround, see sqlalchemy#9175
    posted_at: Mapped[datetime_tz_onupdate]

    valid_on: Mapped[date] = mapped_column(
        server_default=func.current_timestamp(), index=True
    )

    confirmed: Mapped[bool] = mapped_column(default=True)

    # backrefs
    splits: Mapped[list[Split]] = relationship(
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
    bank_account_activities: Mapped[list[BankAccountActivity]] = relationship(
        back_populates="transaction",
        viewonly=True,
    )
    # /backrefs

    # associations
    accounts: Mapped[list[Account]] = relationship(
        secondary="split", back_populates="transactions", viewonly=True
    )
    # /associations

    @property
    def amount(self):
        return sum(max(split.amount, 0) for split in self.splits)

    @property
    def is_balanced(self):
        return sum(split.amount for split in self.splits) == 0

    @property
    def is_simple(self):
        return len(self.splits) == 2


class Split(IntegerIdModel):
    # positive amount means credit (ger. Haben) and negative credit (ger. Soll)
    amount: Mapped[int] = mapped_column(Money)
    account_id: Mapped[int] = mapped_column(
        ForeignKey(Account.id, ondelete="CASCADE"),
        index=True,
    )
    account: Mapped[Account] = relationship(back_populates="splits")

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey(Transaction.id, ondelete="CASCADE"),
    )
    transaction: Mapped[Transaction] = relationship(back_populates="splits")
    __table_args__ = (UniqueConstraint(transaction_id, account_id),)

    # backrefs
    bank_account_activity: Mapped[BankAccountActivity | None] = relationship(
        uselist=False,
    )
    # /backrefs


manager.add_function(
    Split.__table__,
    ddl.Function(
        'split_check_transaction_balanced', [], 'trigger',
        """
        DECLARE
          s split;
          count integer;
          balance integer;
          transaction_deleted boolean;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            s := OLD;
          ELSE
            s := COALESCE(NEW, OLD);
          END IF;

          SELECT COUNT(*) = 0 INTO transaction_deleted FROM "transaction" WHERE "id" = s.transaction_id;

          SELECT COUNT(*), SUM(amount) INTO STRICT count, balance FROM split
              WHERE transaction_id = s.transaction_id;
          IF count < 2 AND NOT transaction_deleted THEN
            RAISE EXCEPTION 'transaction %% has less than two splits',
            s.transaction_id
            USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          IF balance <> 0 THEN
            RAISE EXCEPTION 'transaction %% not balanced',
                s.transaction_id
                USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NULL;
        END;
        """,
        volatility='stable', strict=True, language='plpgsql'
    )
)

manager.add_constraint_trigger(
    Split.__table__,
    ddl.ConstraintTrigger(
        'split_check_transaction_balanced_trigger',
        Split.__table__, ('INSERT', 'UPDATE', 'DELETE'),
        'split_check_transaction_balanced()',
        deferrable=True, initially_deferred=True,
    )
)


class IllegalTransactionError(PycroftModelException):
    """Indicates an attempt to persist an illegal Transaction."""
    pass


# noinspection PyUnusedLocal
@event.listens_for(Transaction, "before_insert")
@event.listens_for(Transaction, "before_update")
def check_transaction_on_save(mapper, connection, target):
    """
    Check transaction constraints.

    Transaction must be balanced, an account mustn't be referenced by more than
    one split and it must consist of at least two splits.
    :raises: IllegalTransactionError if transaction contains errors
    """
    if not target.is_balanced:
        raise IllegalTransactionError(gettext("Transaction is not balanced."))
    if len(target.splits) < 2:
        raise IllegalTransactionError(gettext("Transaction must consist "
                                              "of at least two splits."))


# noinspection PyUnusedLocal
@event.listens_for(Split, "before_update")
@event.listens_for(Split, "after_delete")
def check_split_on_update(mapper, connection, target):
    if not target.transaction.is_balanced:
        raise IllegalTransactionError(gettext("Transaction is not balanced."))


event.listen(Transaction, "before_insert", check_transaction_on_save)
event.listen(Transaction, "before_update", check_transaction_on_save)


class BankAccount(IntegerIdModel):
    name: Mapped[str255]
    bank: Mapped[str255]
    account_number: Mapped[str] = mapped_column(String(10))
    routing_number: Mapped[str] = mapped_column(String(8))
    iban: Mapped[str] = mapped_column(String(34))
    bic: Mapped[str] = mapped_column(String(11))
    fints_endpoint: Mapped[str]
    account_id: Mapped[int] = mapped_column(ForeignKey(Account.id), unique=True)
    account: Mapped[Account] = relationship()

    __table_args__ = (
        UniqueConstraint(account_number, routing_number),
        UniqueConstraint(iban),
    )

    # backrefs
    activities: Mapped[list[BankAccountActivity]] = relationship(
        back_populates="bank_account",
        viewonly=True,
    )
    mt940_errors: Mapped[list[MT940Error]] = relationship(
        back_populates="bank_account", viewonly=True
    )
    # /backrefs

    @hybrid_property
    def _balance(self) -> Decimal:
        return object_session(self).execute(
            select(func.coalesce(func.sum(BankAccountActivity.amount), 0))
                .where(BankAccountActivity.bank_account_id == self.id)
        ).scalar()

    @_balance.expression
    def balance(cls) -> Select[tuple[Decimal]]:
        return select(
            [func.coalesce(func.sum(BankAccountActivity.amount), 0)]
        ).where(
            BankAccountActivity.bank_account_id == cls.id
        ).label("balance")

    @hybrid_property
    def last_imported_at(self) -> DateTimeTz:
        return object_session(self).execute(
                    select(func.max(BankAccountActivity.imported_at))
                    .where(BankAccountActivity.bank_account_id == self.id)
                ).fetchone()[0]


class BankAccountActivity(IntegerIdModel):
    bank_account_id: Mapped[int] = mapped_column(ForeignKey(BankAccount.id), index=True)
    bank_account: Mapped[BankAccount] = relationship(back_populates="activities")
    amount: Mapped[int] = mapped_column(Money)
    reference: Mapped[str] = mapped_column(Text)
    other_account_number: Mapped[str255]
    other_routing_number: Mapped[str255]
    other_name: Mapped[str255]
    imported_at: Mapped[utc.DateTimeTz]
    posted_on: Mapped[date]
    valid_on: Mapped[date]
    transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey(Transaction.id, onupdate="CASCADE", ondelete="SET NULL")
    )
    transaction: Mapped[Transaction | None] = relationship(
        back_populates="bank_account_activities",
        overlaps="bank_account_activity",
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey(Account.id, onupdate="CASCADE", ondelete="SET NULL")
    )
    account: Mapped[Account | None] = relationship(viewonly=True)
    split: Mapped[Split] = relationship(
        foreign_keys=(transaction_id, account_id),
        back_populates="bank_account_activity",
        overlaps="transaction",
    )

    # associations
    matching_patterns: Mapped[list[AccountPattern]] = relationship(
        primaryjoin='foreign(BankAccountActivity.reference)'
                    '.op("~*", is_comparison=True)(remote(AccountPattern.pattern))',
        uselist=True,
        viewonly=True
    )
    # associations

    __table_args__ = (
        ForeignKeyConstraint((transaction_id, account_id),
                             (Split.transaction_id, Split.account_id),
                             onupdate='CASCADE',
                             ondelete='SET NULL'),
        UniqueConstraint(transaction_id, account_id),
    )


class MT940Error(IntegerIdModel):
    mt940: Mapped[str] = mapped_column(Text())
    exception: Mapped[str] = mapped_column(Text())
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    author: Mapped[User] = relationship()
    imported_at: Mapped[datetime_tz_onupdate]
    bank_account: Mapped[BankAccount] = relationship(back_populates="mt940_errors")
    bank_account_id: Mapped[int] = mapped_column(ForeignKey(BankAccount.id))



manager.add_constraint(
    BankAccount.__table__,
    CheckConstraint(
        "account_is_type(account_id, 'BANK_ASSET')",
        name='bank_account_account_type_check',
        table=BankAccount.__table__,
    ),
    dialect='postgresql'
)

manager.add_function(
    BankAccountActivity.__table__,
    ddl.Function(
        'bank_account_activity_matches_referenced_split', [],
        'trigger',
        """
        DECLARE
          v_activity bank_account_activity;
          v_bank_account_account_id integer;
          v_split split;
        BEGIN
          IF TG_OP = 'DELETE' THEN
            v_activity := OLD;
          ELSE
            v_activity := COALESCE(NEW, OLD);
          END IF;

          SELECT bank_account.account_id INTO v_bank_account_account_id FROM bank_account
              WHERE bank_account.id = v_activity.bank_account_id;
          SELECT * INTO v_split FROM split
              WHERE split.transaction_id = v_activity.transaction_id
              AND split.account_id = v_activity.account_id;
          IF v_bank_account_account_id <> v_activity.account_id THEN
            RAISE EXCEPTION 'bank_account_activity %%: account_id of referenced bank_account %%  is different (%% <> %%)',
                v_activity.id, v_activity.bank_account_id, v_activity.account_id, v_bank_account_account_id
                USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          IF v_split IS NOT NULL AND v_split.amount <> v_activity.amount THEN
            RAISE EXCEPTION 'bank_account_activity %%: amount of referenced split %% is different (%% <> %%)',
                v_activity.id, v_split.id, v_activity.amount, v_split.amount
                USING ERRCODE = 'integrity_constraint_violation';
          END IF;
          RETURN NULL;
        END;
        """,
        volatility='stable', strict=True, language='plpgsql'
    )
)


manager.add_constraint_trigger(
    BankAccountActivity.__table__,
    ddl.ConstraintTrigger(
        'bank_account_activity_matches_referenced_split_trigger',
        BankAccountActivity.__table__,
        ('INSERT', 'UPDATE', 'DELETE'),
        'bank_account_activity_matches_referenced_split()',
        deferrable=True, initially_deferred=True,
    )
)

manager.register()
