# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

from datetime import datetime
from dateutil.relativedelta import relativedelta
from pycroft.model.finance import Semester, FinanceAccount, Transaction, Split,\
    Journal, JournalEntry
from pycroft.model import session
from pycroft.lib import config
import csv
from pycroft.lib.all import with_transaction


@with_transaction
def create_semester(name, registration_fee, semester_fee, begin_date, end_date):
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
    return semester


@with_transaction
def simple_transaction(message, debit_account, credit_account, semester, amount,
                       date=None):
    """
    Creates a simple transaction.
    A simple transaction is a transaction that consists of exactly two splits.
    :param message: Transaction message
    :param debit_account: Debit (germ. Soll) account.
    :param credit_account: Credit (germ. Haben) account
    :param semester: Semester of the transaction.
    :param amount: Amount in Eurocents
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


def import_csv(csv_file, import_date=None):
    if import_date is None:
        now = datetime.now()
    else:
        now = import_date

    with open(csv_file, 'r') as csv_file_handle:
        content = csv.reader(csv_file_handle, delimiter=";")

        for fields in content:

            if fields[9] != "EUR":
                raise Exception("The only supported currency is EUR! "
                                + fields[9] + " is invalid!")

            valid_journal = Journal.q.filter_by(account_number=fields[0]).first()

            if valid_journal is None:
                raise Exception("The Journal with the account number '" + fields[0]
                                + "' does not exist in the database!")

            parsed_transaction_date = datetime.strptime(fields[1], "%d.%m")
            if parsed_transaction_date + relativedelta(year=now.year) <= now:
                transaction_date = parsed_transaction_date + relativedelta(year=now.year)
            else:
                transaction_date = parsed_transaction_date + relativedelta(year=now.year - 1)

            valid_date = datetime.strptime(fields[2], "%d.%m.%y")

            entry = JournalEntry(amount=float(fields[8].replace(u",", u".")),
                                 message=fields[4],
                                 journal=valid_journal,
                                 other_account=fields[6],
                                 other_bank=fields[7],
                                 other_person=fields[5],
                                 original_message=fields[4],
                                 import_date=datetime.now(),
                                 transaction_date=transaction_date.date(),
                                 valid_date=valid_date)
            session.session.add(entry)