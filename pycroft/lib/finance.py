# -*- coding: utf-8 -*-
# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'Florian Österreich'

from datetime import datetime
from pycroft.model.finance import Semester, FinanceAccount, Transaction, Split
from pycroft.model import session
from pycroft.lib import config


def create_semester(name, registration_fee, semester_fee, begin_date, end_date,
                    commit=True):
    """
    This function creates a new Semester.
    There are created a registration fee account and a semester fee account
    which ones are attached to the semester
    The name could be something like: "Wintersemester 2012/13"
    :param name: A useful name for the semester.
    :param registration_fee: The fee a student have to pay when he moves in first.
    :param semester_fee: The fee a student have to pay every semester.
    :param begin_date: Date when the semester starts.
    :param end_date: Date when semester ends.
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: The created Semester.
    """
    semester = Semester(name=name,
                        registration_fee=registration_fee,
                        semester_fee=semester_fee,
                        begin_date=begin_date,
                        end_date=end_date)

    objects = [semester]
    for account in config.get("finance")["semester_accounts"]:
        objects.append(
            FinanceAccount(type=account["type"], name=account["name"],
                           semester=semester, tag=account["tag"]))

    session.session.add_all(objects)
    if commit:
        session.session.commit()
    return semester


def simple_transaction(message, debit_account, credit_account, semester, amount,
                       date=None, commit=True):
    """
    Creates a simple transaction.
    A simple transaction is a transaction that consists of exactly two splits.
    This function does not commit the changes to the database.
    :param message: Transaction message
    :param debit_account: Debit (germ. Soll) account.
    :param credit_account: Credit (germ. Haben) account
    :param semester: Semester of the transaction.
    :param amount: Amount in Eurocents
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    """
    if date is None:
        date = datetime.now()
    new_transaction = Transaction(
        message=message,
        transaction_date=date, semester=semester)
    new_debit_split = Split(
        amount=amount,
        account=debit_account,
        transaction=new_transaction)
    new_credit_split = Split(
        amount=-amount,
        account=credit_account,
        transaction=new_transaction)
    session.session.add_all(
        [new_transaction, new_debit_split, new_credit_split]
    )
    if commit:
        session.session.commit()
