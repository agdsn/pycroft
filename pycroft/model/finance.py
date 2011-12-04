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
    name = Column(String(127))
    type = Column(Enum("LIABILITY", "EXPENSE", "ASSET", "INCOME", "EQUITY",
                        name="financeaccounttypes"))

    # many to one from FinanceAccount to User
    user = relationship("User", backref=backref("finance_accounts"))
    user_id = Column(Integer, ForeignKey("user.id"))


class Journal(ModelBase):
    account = Column(String(255))
    bank = Column(String(255))
    hbci_url = Column(String(255))
    last_update = Column(DateTime())


class JournalEntry(ModelBase):
    message = Column(Text())
    journal_id = Column(Integer(), ForeignKey("journal.id"))
    journal = relationship("Journal", backref=backref("entries"))
    other_account = Column(String(255))
    other_bank = Column(String(255))
    other_person = Column(String(255))
    original_message = Column(Text())
    timestamp = Column(DateTime())


class Transaction(ModelBase):
    message = Column(Text())
    journal_entry_id = Column(Integer(), ForeignKey("journalentry.id"))
    journal_entry = relationship("JournalEntry",
                                    backref=backref("transaction"))


class Split(ModelBase):
    amount = Column(Integer())
    from_account_id = Column(Integer(), ForeignKey("financeaccount.id"))
    from_account = relationship("FinanceAccount")
    to_account_id = Column(Integer(), ForeignKey("financeaccount.id"))
    to_account = relationship("FinanceAccount")
    transaction_id = Column(Integer(), ForeignKey("transaction.id"))
    transaction = relationship("Transaction", backref=backref("splits"))
