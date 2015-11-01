# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import operator
from sqlalchemy.ext.hybrid import hybrid_property
from .base import ModelBase
from sqlalchemy import ForeignKey, event, func, select
from sqlalchemy import Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import (
    Date, DateTime, Enum, Integer, Interval, String, Text)
from sqlalchemy.schema import CheckConstraint, UniqueConstraint

from .functions import utcnow
from pycroft._compat import imap
from pycroft.helpers.interval import closed
from pycroft.helpers.i18n import gettext


class Semester(ModelBase):
    name = Column(String, nullable=False)
    registration_fee = Column(Integer, CheckConstraint('registration_fee >= 0'),
                              nullable=False)
    regular_semester_fee = Column(Integer,
                                  CheckConstraint('regular_semester_fee >= 0'),
                                  nullable=False)
    reduced_semester_fee = Column(Integer,
                                  CheckConstraint('reduced_semester_fee >= 0'),
                                  nullable=False)
    late_fee = Column(Integer, CheckConstraint('late_fee >= 0'), nullable=False)
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
    allowed_overdraft = Column(Integer,
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
                       "LIABILITY",   # Passivkonto
                       "EXPENSE",     # Aufwandskonto
                       "REVENUE",     # Ertragskonto
                       name="account_type"),
                  nullable=False)

    transactions = relationship("Transaction", secondary="split",
                                backref="accounts")

    @hybrid_property
    def balance(self):
        return sum(imap(operator.attrgetter("amount"), self.splits))

    @balance.expression
    def balance(self):
        return select(
            [func.sum(Split.amount)]
        ).where(
            Split.account_id == self.id
        ).label("balance")


class BankAccount(ModelBase):
    name = Column(String(255), nullable=False)
    bank = Column(String(255), nullable=False)
    account_number = Column(String(10), nullable=False)
    routing_number = Column(String(8), nullable=False)
    iban = Column(String(34), nullable=False)
    bic = Column(String(11), nullable=False)
    hbci_url = Column(String(255), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False,
                        unique=True)
    account = relationship(Account)

    __table_args__ = (
        UniqueConstraint(account_number, routing_number),
        UniqueConstraint(iban),
    )

    @hybrid_property
    def last_update(self):
        return max(imap(lambda e: e.import_time, self.activities))

    @last_update.expression
    def last_update(self):
        return (
            select(func.max(BankAccountActivity.import_time))
            .where(BankAccountActivity.bank_account_id == self.id)
            .label("last_update")
        )


class BankAccountActivity(ModelBase):
    bank_account_id = Column(Integer, ForeignKey(BankAccount.id),
                             nullable=False)
    bank_account = relationship(BankAccount, backref=backref("activities"))
    amount = Column(Integer, nullable=False)
    reference = Column(Text, nullable=False)
    original_reference = Column(Text, nullable=False)
    other_account_number = Column(String(255), nullable=False)
    other_routing_number = Column(String(255), nullable=False)
    other_name = Column(String(255), nullable=False)
    import_time = Column(DateTime, nullable=False)
    posted_at = Column(Date, nullable=False)
    valid_on = Column(Date, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transaction.id"), unique=True)
    transaction = relationship("Transaction",
                               backref=backref("bank_account_activity",
                                               uselist=False))


class IllegalTransactionError(Exception):
    """Indicates an attempt to persist an illegal Transaction."""
    pass


class Transaction(ModelBase):
    description = Column(Text(), nullable=False)
    author_id = Column(Integer, ForeignKey("user.id", ondelete='SET NULL',
                                           onupdate='CASCADE'),
                       nullable=True)
    author = relationship("User")

    posted_at = Column(DateTime, nullable=False,
                       default=utcnow(), onupdate=utcnow())
    valid_on = Column(Date, nullable=False, default=utcnow())

    @property
    def is_balanced(self):
        return sum(split.amount for split in self.splits) == 0

    @property
    def is_simple(self):
        return len(self.splits) == 2


def check_transaction_on_save(mapper, connection, target):
    """
    Check transaction constraints.

    Transaction must be balanced, an account mustn't be referenced by more than
    one split and it must consist of at least two splits.
    The last constraints prohibits transactions on the same account and
    difficulties to calculate the transferred value between two accounts.
    :raises: IllegalTransactionError if transaction contains errors
    """
    if not target.is_balanced:
        raise IllegalTransactionError(gettext(u"Transaction is not balanced."))
    if len(target.splits) < 2:
        raise IllegalTransactionError(gettext(u"Transaction must consist "
                                              u"of at least two splits."))
    marked_accounts = set()
    for split in target.splits:
        if split.account in marked_accounts:
            raise IllegalTransactionError(gettext(u"Transaction must not have "
                                                  u"multiple splits with the "
                                                  u"same account."))
        marked_accounts.add(split.account)


event.listen(Transaction, "before_insert", check_transaction_on_save)
event.listen(Transaction, "before_update", check_transaction_on_save)


class Split(ModelBase):
    # positive amount means credit (ger. Haben) and negative credit (ger. Soll)
    amount = Column(Integer, nullable=False)
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

