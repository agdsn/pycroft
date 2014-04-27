# -*- coding: utf-8 -*-
"""
    pycroft.model.finance
    ~~~~~~~~~~~~~~

    This module contains the classes FinanceAccount, ...

    :copyright: (c) 2011 by AG DSN.
"""
from datetime import datetime
from base import ModelBase
from sqlalchemy import ForeignKey
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
            name="financeaccounttypes"),
        nullable=False
    )
    transactions = relationship("Transaction", secondary="split")


class Journal(ModelBase):
    account = Column(String(255), nullable=False)
    bank = Column(String(255), nullable=False)
    hbci_url = Column(String(255), nullable=False)
    last_update = Column(DateTime, nullable=False)
    account_number = Column(String(34), nullable=False)
    bank_identification_code = Column(String(255), nullable=False)


class JournalEntry(ModelBase):
    amount = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    journal_id = Column(Integer, ForeignKey("journal.id"), nullable=False)
    journal = relationship("Journal", backref=backref("entries"))
    other_account = Column(String(255), nullable=False)
    other_bank = Column(String(255), nullable=False)
    other_person = Column(String(255), nullable=False)
    original_description = Column(Text, nullable=False)
    import_date = Column(DateTime, nullable=False)
    transaction_date = Column(Date, nullable=False)
    valid_date = Column(Date, nullable=False)


class Transaction(ModelBase):
    description = Column(Text(), nullable=False)
    transaction_date = Column(DateTime, nullable=False, default=datetime.now)

    journal_entry_id = Column(
        Integer(), ForeignKey("journalentry.id"),
        nullable=True)
    journal_entry = relationship(
        "JournalEntry", backref=backref("transactions"))

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
        Integer, ForeignKey("financeaccount.id"), nullable=False)
    account = relationship("FinanceAccount")
    transaction_id = Column(
        Integer, ForeignKey("transaction.id", ondelete='CASCADE'),
        nullable=False)
    transaction = relationship(
        "Transaction", backref=backref("splits", cascade="all, delete-orphan"))
