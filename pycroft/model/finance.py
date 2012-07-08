# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
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
from sqlalchemy import event


class FinanceAccount(ModelBase):
    name = Column(String(127), nullable=False)
    type = Column(Enum("LIABILITY", "EXPENSE", "ASSET", "INCOME", "EQUITY",
                        name="financeaccounttypes"), nullable=False)

    transactions = relationship("Transaction", secondary="split")

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

    @property
    def is_balanced(self):
        print [split.amount for split in self.splits]
        return sum([split.amount for split in self.splits]) == 0


def check_transaction_balance_on_save(mapper, connection, target):
    if not target.is_balanced:
        raise Exception('Transaction "%s" is not balanced!' % target.message)


event.listen(Transaction, "before_insert", check_transaction_balance_on_save)
event.listen(Transaction, "before_update", check_transaction_balance_on_save)


class Split(ModelBase):
    amount = Column(Integer(), nullable=False)
    account_id = Column(Integer(), ForeignKey("financeaccount.id"),
                                nullable=False)
    account = relationship("FinanceAccount")
    transaction_id = Column(Integer(), ForeignKey("transaction.id"),
                                nullable=False)
    transaction = relationship("Transaction", backref=backref("splits"))
