# -*- coding: utf-8 -*-
import cStringIO
from itertools import imap, groupby
from collections import namedtuple
from sqlalchemy.orm.exc import NoResultFound

__author__ = 'Florian Österreich'

from datetime import datetime, date
from sqlalchemy import desc
from pycroft.model.finance import Semester, FinanceAccount, Transaction, Split,\
    Journal, JournalEntry
from pycroft.model import session
import csv
from pycroft.lib.all import with_transaction


@with_transaction
def create_semester(name, registration_fee, regular_membership_fee,
                    reduced_membership_fee, overdue_fine, premature_begin_date,
                    begin_date, end_date, belated_end_date):
    """
    Creates a new Semester.

    The name could be something like: "Wintersemester 2012/13"
    :param name: A useful name for the semester.
    :param registration_fee: Fee every new member is required to pay after
        sign-up.
    :param regular_membership_fee: Regular per semester membership fee.
    :param reduced_membership_fee: Reduced per semester membership fee.
    :param overdue_fine: Fine for not paying fees in acceptable time.
    :param premature_begin_date: Date before begin_date, after which members
        will not be charged for the previous semester
    :param begin_date: Date when the semester starts.
    :param end_date: Date when semester ends..
    :param belated_end_date: Date after end_date, before which members will not
        be charged for the next semester.
    :return The created Semester.
    """
    semester = Semester(name=name,
                        registration_fee=registration_fee,
                        regular_membership_fee=regular_membership_fee,
                        reduced_membership_fee=reduced_membership_fee,
                        overdue_fine=overdue_fine,
                        premature_begin_date=premature_begin_date,
                        begin_date=begin_date,
                        end_date=end_date,
                        belated_end_date=belated_end_date,
                        )
    session.session.add(semester)
    return semester


@with_transaction
def simple_transaction(description, debit_account, credit_account,
                       amount, valid_date=None):
    """
    Posts a simple transaction.
    A simple transaction is a transaction that consists of exactly two splits.
    The current system date will be used as transaction date, an optional valid
    date may be specified.
    :param str description: Description
    :param FinanceAccount debit_account: Debit (germ. Soll) account.
    :param FinanceAccount credit_account: Credit (germ. Haben) account
    :param int amount: Amount in Eurocents
    :param valid_date: Date, when the transaction should be valid. Current
    system date, if omitted.
    :type valid_date: date or None
    """
    if valid_date is None:
        valid_date = date.today()
    new_transaction = Transaction(
        description=description,
        valid_date=valid_date)
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
    return new_transaction


@with_transaction
def complex_transaction(description, splits, valid_date=None):
    if valid_date is None:
        valid_date = date.now()
    objects = []
    new_transaction = Transaction(
        description=description,
        valid_date=valid_date)
    objects.append(new_transaction)
    transaction_sum = 0
    for (account, amount) in splits:
        transaction_sum += amount
        new_split = Split(
            amount=amount, account=account, transaction=new_transaction)
        objects.append(new_split)
    if transaction_sum != 0:
        raise ValueError('Split amounts do not sum up to zero.')
    session.session.add_all(objects)


MT940_FIELDNAMES = [
    'our_account_number',
    'transaction_date',
    'valid_date',
    'type',
    'description',
    'other_name',
    'other_account_number',
    'other_routing_number',
    'amount',
    'currency',
    'info',
]


MT940Record = namedtuple("MT940Record", MT940_FIELDNAMES)


class MT940Dialect(csv.Dialect):
    delimiter = ";"
    quotechar = '"'
    doublequote = True
    skipinitialspace = True
    lineterminator = '\n'
    quoting = csv.QUOTE_ALL


def import_journal_csv(csv_file, import_time=None):
    if import_time is None:
        import_time = datetime.now()

    # Convert to MT940Record and enumerate
    reader = csv.DictReader(csv_file, MT940_FIELDNAMES, dialect=MT940Dialect)
    records = enumerate(imap(lambda r: MT940Record(**r), reader), 1)
    # Skip first record (header)
    try:
        records.next()
    except StopIteration:
        raise Exception(u"Leerer Datensatz.")

    session.session.add_all(imap(
        lambda r: process_record(r[0], r[1], import_time),
        reversed(list(records))
    ))
    session.session.commit()


def cleanup_description(description):
    return description


def restore_record(record):
    string_buffer = cStringIO.StringIO()
    csv.DictWriter(
        string_buffer, MT940_FIELDNAMES, dialect=MT940Dialect
    ).writerow(record._asdict())
    restored_record = string_buffer.getvalue()
    string_buffer.close()
    return restored_record


def process_record(index, record, import_time):
    if record.currency != "EUR":
        message = u"Nicht unterstützte Währung {0} in Datensatz {1}: {2}"
        raw_record = restore_record(record)
        raise Exception(
            message.format(record.currency, index, raw_record)
        )
    try:
        journal = Journal.q.filter_by(
            account_number=record.our_account_number
        ).one()
    except NoResultFound:
        message = u"Kein Journal mit der Kontonummer {0} gefunden."
        raise Exception(message.format(record.our_account_number))

    try:
        valid_date = datetime.strptime(record.valid_date, "%d.%m.%y").date()
        transaction_date = (datetime
                            .strptime(record.transaction_date, "%d.%m")
                            .date())
    except ValueError:
        message = u"Unbekanntes Datumsformat in Datensatz {0}: {1}"
        raw_record = restore_record(record)
        raise Exception(message.format(index, raw_record))

    # Assume that transaction_date's year is the same
    transaction_date = transaction_date.replace(year=valid_date.year)
    # The transaction_date may not be after valid_date, if it is, our
    # assumption was wrong
    if transaction_date > valid_date:
        transaction_date = transaction_date.replace(
            year=transaction_date.year - 1
        )
    return JournalEntry(
        amount=int(record.amount.replace(u",", u"")),
        journal=journal,
        description=cleanup_description(record.description),
        original_description=record.description,
        other_account_number=record.other_account_number,
        other_routing_number=record.other_routing_number,
        other_name=record.other_name,
        import_time=import_time,
        transaction_date=transaction_date,
        valid_date=valid_date
    )
