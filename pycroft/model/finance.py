# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.finance
    ~~~~~~~~~~~~~~

    This module contains the classes FinanceAccount, ...

    :copyright: (c) 2011 by AG DSN.
"""
import datetime
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Table, Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Enum, Integer, Text, DateTime, String, Date
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy import event


class Semester(ModelBase):
    name = Column(String, nullable=False)
    semester_fee = Column(Integer, nullable=False)
    registration_fee = Column(Integer, nullable=False)
    begin_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)


class FinanceAccount(ModelBase):
    name = Column(String(127), nullable=False)
    # LIABILITY=Passivkonto,
    # EXPENSE=Aufwandskonto,
    # ASSET=Aktivkonto,
    # INCOME=Ertragskonto
    type = Column(
        Enum("LIABILITY", "EXPENSE", "ASSET", "INCOME", "EQUITY",
             name="financeaccounttypes"),
        nullable=False
    )

    transactions = relationship("Transaction", secondary="split")
    semester_id = Column(Integer, ForeignKey('semester.id'), nullable=True)
    semester = relationship("Semester", backref=backref("accounts"))
    tag = Column(Enum("registration_fee","additional_fee","regular_fee","arrears_fee"), nullable=True)
    __table_args__ = (UniqueConstraint("semester_id", "tag"),)


class Journal(ModelBase):
    account = Column(String(255), nullable=False)
    bank = Column(String(255), nullable=False)
    hbci_url = Column(String(255), nullable=False)
    last_update = Column(DateTime, nullable=False)
    account_number = Column(String(34), nullable=False)
    bank_identification_code = Column(String(255), nullable=False)


class JournalEntry(ModelBase):
    amount = Column(Integer, nullable=False)
    message = Column(Text, nullable=False)
    journal_id = Column(Integer, ForeignKey("journal.id"), nullable=False)
    journal = relationship("Journal", backref=backref("entries"))
    other_account = Column(String(255), nullable=False)
    other_bank = Column(String(255), nullable=False)
    other_person = Column(String(255), nullable=False)
    original_message = Column(Text, nullable=False)
    import_date = Column(DateTime, nullable=False)
    transaction_date = Column(Date, nullable=False)
    valid_date = Column(Date, nullable=False)


class Transaction(ModelBase):
    message = Column(Text(), nullable=False)
    transaction_date = Column(DateTime, nullable=False, default=datetime.datetime.now)

    journal_entry_id = Column(Integer(), ForeignKey("journalentry.id"),
                                                            nullable=True)
    journal_entry = relationship("JournalEntry",
                                    backref=backref("transactionu"))

    semester_id = Column(Integer, ForeignKey("semester.id"))
    semester = relationship("Semester", backref=backref("transactions"))

    @property
    def is_balanced(self):
        return sum([split.amount for split in self.splits]) == 0


def check_transaction_balance_on_save(mapper, connection, target):
    assert target.is_balanced, 'Transaction "%s" is not balanced!' % target.message


event.listen(Transaction, "before_insert", check_transaction_balance_on_save)
event.listen(Transaction, "before_update", check_transaction_balance_on_save)


#soll ist positiv, haben ist negativ
class Split(ModelBase):
    amount = Column(Integer, nullable=False)
    account_id = Column(Integer, ForeignKey("financeaccount.id"),
                                nullable=False)
    account = relationship("FinanceAccount")

    transaction_id = Column(Integer, ForeignKey("transaction.id",
                                ondelete='CASCADE'),
                                nullable=False)
    transaction = relationship("Transaction", backref=backref("splits", cascade="all, delete-orphan"))
