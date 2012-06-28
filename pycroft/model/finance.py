# -*- coding: utf-8 -*-
"""
    pycroft.model.finance
    ~~~~~~~~~~~~~~

    This module contains the classes FinanceAccount, ...

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Table, Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Enum, Integer, Text, DateTime
from sqlalchemy.types import String


class FinanceAccount(ModelBase):
    name = Column(String(127), nullable=False)
    type = Column(Enum("LIABILITY", "EXPENSE", "ASSET", "INCOME", "EQUITY",
        name="financeaccounttypes"), nullable=False)

    # many to one from FinanceAccount to User
    user = relationship("User", backref=backref("finance_accounts"))
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)


class Journal(ModelBase):
    account = Column(String(255), nullable=False)
    bank = Column(String(255), nullable=False)
    hbci_url = Column(String(255), nullable=False)
    last_update = Column(DateTime(), nullable=False)


class JournalEntry(ModelBase):
    amount = Column(Integer(), nullable=False)
    message = Column(Text(), nullable=True)
    journal_id = Column(Integer(), ForeignKey("journal.id"), nullable=False)
    journal = relationship("Journal", backref=backref("entries"))
    other_account = Column(String(255), nullable=False)
    other_bank = Column(String(255), nullable=False)
    other_person = Column(String(255), nullable=False)
    original_message = Column(Text(), nullable=False)
    timestamp = Column(DateTime(), nullable=False)


class Transaction(ModelBase):
    message = Column(Text(), nullable=False)
    journal_entry_id = Column(Integer(), ForeignKey("journalentry.id"),
        nullable=True)
    journal_entry = relationship("JournalEntry",
        backref=backref("transaction"))


class Split(ModelBase):
    amount = Column(Integer(), nullable=False)
    from_account_id = Column(Integer(), ForeignKey("financeaccount.id"),
        nullable=False)
    from_account = relationship("FinanceAccount")
    to_account_id = Column(Integer(), ForeignKey("financeaccount.id"),
        nullable=False)
    to_account = relationship("FinanceAccount")
    transaction_id = Column(Integer(), ForeignKey("transaction.id"),
        nullable=False)
    transaction = relationship("Transaction", backref=backref("splits"))
