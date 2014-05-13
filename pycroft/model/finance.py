# -*- coding: utf-8 -*-
"""
    pycroft.model.finance
    ~~~~~~~~~~~~~~

    This module contains the classes FinanceAccount, ...

    :copyright: (c) 2011 by AG DSN.
"""
from datetime import datetime
from itertools import imap
from sqlalchemy.ext.hybrid import hybrid_property
from base import ModelBase
from sqlalchemy import ForeignKey, func, select
from sqlalchemy import Table, Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Enum, Integer, Text, DateTime, String, Date
from sqlalchemy.schema import CheckConstraint, UniqueConstraint
from sqlalchemy import event


class Semester(ModelBase):
    name = Column(String, nullable=False)
    registration_fee = Column(Integer, nullable=False)
    regular_membership_fee = Column(Integer, nullable=False)
    reduced_membership_fee = Column(Integer, nullable=False)
    overdue_fine = Column(Integer, nullable=False)
    premature_begin_date = Column(Date, nullable=False)
    begin_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    belated_end_date = Column(Date, nullable=False)
    __table_args__ = (
        CheckConstraint('registration_fee > 0'),
        CheckConstraint('regular_membership_fee > 0'),
        CheckConstraint('reduced_membership_fee > 0'),
        CheckConstraint('overdue_fine > 0'),
        CheckConstraint('premature_begin_date < begin_date'),
        CheckConstraint('begin_date < end_date'),
        CheckConstraint('end_date < belated_end_date'),
    )


class FinanceAccount(ModelBase):
    name = Column(String(127), nullable=False)
    type = Column(
        Enum(
            "ASSET",      # Aktivkonto
            "LIABILITY",  # Passivkonto
            "EXPENSE",    # Aufwandskonto
            "REVENUE",    # Ertragskonto
            name="finance_account_type"),
        nullable=False
    )
    transactions = relationship("Transaction", secondary="split")


class Journal(ModelBase):
    name = Column(String(255), nullable=False)
    bank = Column(String(255), nullable=False)
    account_number = Column(String(10), nullable=False)
    routing_number = Column(String(8), nullable=False)
    iban = Column(String(34), nullable=False)
    bic = Column(String(11), nullable=False)
    hbci_url = Column(String(255), nullable=False)
    finance_account_id = Column(
        Integer, ForeignKey("finance_account.id"), nullable=False)
    finance_account = relationship("FinanceAccount")
    __tableargs__ = [
        UniqueConstraint(account_number, routing_number),
        UniqueConstraint(iban),
    ]

    @hybrid_property
    def last_update(self):
        return max(imap(lambda e: e.import_time, self.entries))


    @last_update.expression
    def last_update(self):
        return (
            select(func.max(JournalEntry.import_time))
            .where(JournalEntry.journal_id == self.id)
            .label("last_update")
        )


class JournalEntry(ModelBase):
    journal_id = Column(Integer, ForeignKey("journal.id"), nullable=False)
    journal = relationship("Journal", backref=backref("entries"))
    amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    original_description = Column(Text, nullable=False)
    other_account_number = Column(String(255), nullable=False)
    other_routing_number = Column(String(255), nullable=False)
    other_name = Column(String(255), nullable=False)
    import_time = Column(DateTime, nullable=False)
    transaction_date = Column(Date, nullable=False)
    valid_date = Column(Date, nullable=False)
    transaction_id = Column(Integer, ForeignKey("transaction.id"))
    transaction = relationship("Transaction")


class Transaction(ModelBase):
    description = Column(Text(), nullable=False)
    transaction_date = Column(DateTime, nullable=False, default=datetime.now)
    valid_date = Column(Date, nullable=False, default=datetime.now)

    @property
    def is_balanced(self):
        return sum([split.amount for split in self.splits]) == 0


def check_transaction_balance_on_save(mapper, connection, target):
    assert target.is_balanced, 'Transaction "%s" is not balanced!' % target.description


event.listen(Transaction, "before_insert", check_transaction_balance_on_save)
event.listen(Transaction, "before_update", check_transaction_balance_on_save)


#soll ist positiv, haben ist negativ
class Split(ModelBase):
    amount = Column(Integer, nullable=False)
    account_id = Column(
        Integer,
        ForeignKey("finance_account.id", ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )
    account = relationship(
        "FinanceAccount",
        backref=backref("splits", cascade="all, delete-orphan")
    )
    transaction_id = Column(
        Integer,
        ForeignKey("transaction.id", ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False
    )
    transaction = relationship(
        "Transaction",
        backref=backref("splits", cascade="all, delete-orphan")
    )
