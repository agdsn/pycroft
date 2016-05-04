# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import operator

from sqlalchemy import Column, ForeignKey, event, func, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import (
    CheckConstraint, ForeignKeyConstraint, UniqueConstraint)
from sqlalchemy.types import (
    Date, DateTime, Enum, Integer, Interval, String, Text)

from pycroft._compat import imap
from pycroft.helpers.i18n import gettext
from pycroft.helpers.interval import closed
from pycroft.model import ddl
from pycroft.model.types import Money
from .base import ModelBase
from .functions import utcnow

manager = ddl.DDLManager()


class Semester(ModelBase):
    name = Column(String, nullable=False)
    registration_fee = Column(Money, CheckConstraint('registration_fee >= 0'),
                              nullable=False)
    regular_semester_fee = Column(Money,
                                  CheckConstraint('regular_semester_fee >= 0'),
                                  nullable=False)
    reduced_semester_fee = Column(Money,
                                  CheckConstraint('reduced_semester_fee >= 0'),
                                  nullable=False)
    late_fee = Column(Money, CheckConstraint('late_fee >= 0'), nullable=False)
    # Timedelta a person has to be member in a semester to be charged any
    # semester fee at all(grace period)
    grace_period = Column(Interval, nullable=False)
    # Timedelta a member has to be present (i.e. not away although being member)
    # in a semester to be charged the full fee
    reduced_semester_fee_threshold = Column(Interval, nullable=False)
    # Timedelta after which members are being charged a late fee for not paying
    # in time
    payment_deadline = Column(Interval, nullable=False)
    # Amount of outstanding debt a member can have without being charged a late
    # fee
    allowed_overdraft = Column(Money,
                               CheckConstraint('allowed_overdraft >= 0'),
                               nullable=False)
    begins_on = Column(Date, nullable=False)
    ends_on = Column(Date, nullable=False)

    def __contains__(self, date):
        return date in closed(self.begins_on, self.ends_on)

    __table_args__ = (
        CheckConstraint('begins_on < ends_on'),
    )


class Account(ModelBase):
    name = Column(String(127), nullable=False)
    type = Column(Enum("ASSET",       # Aktivkonto
                       "USER_ASSET",  # Aktivkonto for users
                       "BANK_ASSET",  # Aktivkonto for bank accounts
                       "LIABILITY",   # Passivkonto
                       "EXPENSE",     # Aufwandskonto
                       "REVENUE",     # Ertragskonto
                       name="account_type"),
                  nullable=False)

    @hybrid_property
    def balance(self):
        return sum(imap(operator.attrgetter("amount"), self.splits))

    @balance.expression
    def balance(self):
        return select(
            [func.coalesce(func.sum(Split.amount), 0)]
        ).where(
            Split.account_id == self.id
        ).label("balance")


manager.add_function(
    Account.__table__,
    ddl.Function(
        'account_is_type(integer, account_type)', 'boolean',
        "SELECT type = $2 FROM account WHERE id = $1 ",
        volatility='stable', strict=True,
    )
)


class Transaction(ModelBase):
    description = Column(Text(), nullable=False)
    author_id = Column(Integer, ForeignKey("user.id", ondelete='SET NULL',
                                           onupdate='CASCADE'),
                       nullable=True)
    author = relationship("User")
    posted_at = Column(DateTime, nullable=False,
                       default=utcnow(), onupdate=utcnow())
    valid_on = Column(Date, nullable=False, default=utcnow())
    accounts = relationship(Account, secondary="split", backref="transactions")

    @property
    def is_balanced(self):
        return sum(split.amount for split in self.splits) == 0

    @property
    def is_simple(self):
        return len(self.splits) == 2


class Split(ModelBase):
    # positive amount means credit (ger. Haben) and negative credit (ger. Soll)
    amount = Column(Money, nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id, ondelete='CASCADE'),
                        nullable=False)
    account = relationship(Account,
                           backref=backref("splits",
                                           cascade="all, delete-orphan"))

    transaction_id = Column(Integer,
                            ForeignKey(Transaction.id, ondelete='CASCADE'),
                            nullable=False)
    transaction = relationship(Transaction,
                               backref=backref("splits",
                                               cascade="all, delete-orphan"))
    __table_args = (
        UniqueConstraint(transaction_id, account_id),
    )


manager.add_function(
    Split.__table__,
    ddl.Function(
        'split_check_transaction_balanced()', 'trigger',
        """
        DECLARE
          s split;
          count integer;
          balance integer;
        BEGIN
          s := COALESCE(NEW, OLD);
          SELECT COUNT(*), SUM(amount) INTO STRICT count, balance FROM split
              WHERE transaction_id = s.transaction_id;
          IF count < 2 THEN
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
        'split_check_transaction_balanced()'
    )
)


class IllegalTransactionError(Exception):
    """Indicates an attempt to persist an illegal Transaction."""
    pass


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
        raise IllegalTransactionError(gettext(u"Transaction is not balanced."))
    if len(target.splits) < 2:
        raise IllegalTransactionError(gettext(u"Transaction must consist "
                                              u"of at least two splits."))


event.listen(Transaction, "before_insert", check_transaction_on_save)
event.listen(Transaction, "before_update", check_transaction_on_save)


class BankAccount(ModelBase):
    name = Column(String(255), nullable=False)
    bank = Column(String(255), nullable=False)
    account_number = Column(String(10), nullable=False)
    routing_number = Column(String(8), nullable=False)
    iban = Column(String(34), nullable=False)
    bic = Column(String(11), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False,
                        unique=True)
    account = relationship(Account)

    __table_args__ = (
        UniqueConstraint(account_number, routing_number),
        UniqueConstraint(iban),
    )

    @hybrid_property
    def last_updated_at(self):
        return max(imap(operator.attrgetter('imported_at'), self.activities))

    @last_updated_at.expression
    def last_updated_at(self):
        return (
            select(func.max(BankAccountActivity.imported_at))
            .where(BankAccountActivity.bank_account_id == self.id)
            .label("last_updated_at")
        )


class BankAccountActivity(ModelBase):
    bank_account_id = Column(Integer, ForeignKey(BankAccount.id),
                             nullable=False)
    bank_account = relationship(BankAccount, backref=backref("activities"))
    amount = Column(Money, nullable=False)
    reference = Column(Text, nullable=False)
    original_reference = Column(Text, nullable=False)
    other_account_number = Column(String(255), nullable=False)
    other_routing_number = Column(String(255), nullable=False)
    other_name = Column(String(255), nullable=False)
    imported_at = Column(DateTime, nullable=False)
    posted_on = Column(Date, nullable=False)
    valid_on = Column(Date, nullable=False)
    transaction_id = Column(Integer, ForeignKey(Transaction.id))
    transaction = relationship(Transaction, viewonly=True)
    account_id = Column(Integer, ForeignKey(Account.id))
    account = relationship(Account, viewonly=True)
    split = relationship(Split, foreign_keys=(transaction_id, account_id),
                         backref=backref("bank_account_activity",
                                         uselist=False))
    __table_args = (
        ForeignKeyConstraint((transaction_id, account_id),
                             (Split.transaction_id, Split.account_id),
                             onupdate='CASCADE',
                             ondelete='SET NULL'),
        UniqueConstraint(transaction_id, account_id),
    )

BankAccountActivity.__table__.add_is_dependent_on(Split.__table__)

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
        'bank_account_activity_matches_referenced_split()',
        'trigger',
        """
        DECLARE
          v_activity bank_account_activity;
          v_bank_account_account_id integer;
          v_split split;
        BEGIN
          v_activity := COALESCE(NEW, OLD);
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
        'bank_account_activity_matches_referenced_split()'
    )
)

manager.register()
