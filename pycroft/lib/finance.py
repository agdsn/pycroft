# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import imap, chain, izip_longest, ifilter
from collections import namedtuple
import re

import cStringIO
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from pycroft import config
from pycroft.model.user import User


__author__ = 'Florian Österreich'

from datetime import datetime, date
from sqlalchemy import func, between, Integer, cast
from pycroft.model.finance import Semester, FinanceAccount, Transaction, Split,\
    Journal, JournalEntry
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.functions import sign, least
import csv


def get_semester_for_date(target_date):
    """
    Get the semester which contains a given target date.
    :param date target_date: The date for which a corresponding semester should
    be found.
    :rtype: Semester
    :raises sqlalchemy.orm.exc.NoResultFound if no semester was found
    :raises sqlalchemy.orm.exc.MultipleResultsFound if multiple semester were
    found.
    """
    return Semester.q.filter(
        between(target_date, Semester.begin_date, Semester.end_date)
    ).one()


def get_current_semester():
    """
    Get the current semester.
    :rtype: Semester
    """
    return get_semester_for_date(date.today())


def get_registration_fee_account():
    return FinanceAccount.q.filter(
        FinanceAccount.id == config['finance']['registration_fee_account_id']
    ).one()


def get_semester_contribution_account():
    account_id = config['finance']['semester_contribution_account_id']
    return FinanceAccount.q.filter(
        FinanceAccount.id == account_id
    ).one()


@with_transaction
def simple_transaction(description, debit_account, credit_account, amount,
                       author, valid_date=None):
    """
    Posts a simple transaction.
    A simple transaction is a transaction that consists of exactly two splits,
    where one account is debited and another different account is credited with
    the same amount.
    The current system date will be used as transaction date, an optional valid
    date may be specified.
    :param unicode description: Description
    :param FinanceAccount debit_account: Debit (germ. Soll) account.
    :param FinanceAccount credit_account: Credit (germ. Haben) account
    :param int amount: Amount in Eurocents
    :param User author: User who created the transaction
    :param valid_date: Date, when the transaction should be valid. Current
    system date, if omitted.
    :type valid_date: date or None
    :rtype: Transaction
    """
    if valid_date is None:
        valid_date = date.today()
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_date=valid_date)
    new_debit_split = Split(
        amount=-amount,
        account=debit_account,
        transaction=new_transaction)
    new_credit_split = Split(
        amount=amount,
        account=credit_account,
        transaction=new_transaction)
    session.session.add_all(
        [new_transaction, new_debit_split, new_credit_split]
    )
    return new_transaction


def setup_user_finance_account(new_user, processor):
    """Adds initial charges to a new user's finance account.
    :param new_user: the User object of the user moving in
    :param processor: the User object of the user who initiated the action
                      of moving the user in
    :return: None
    """

    conf = config["finance"]
    current_semester = get_current_semester()
    format_args = {
        "user_id": new_user.id,
        "user_name": new_user.name,
        "semester": current_semester.name
    }

    # Initial bookings
    simple_transaction(
        conf["registration_fee_description"].format(**format_args),
        get_registration_fee_account(), new_user.finance_account,
        current_semester.registration_fee, processor
    )
    simple_transaction(
        conf["semester_contribution_description"].format(**format_args),
        get_semester_contribution_account(), new_user.finance_account,
        current_semester.regular_semester_contribution, processor
    )


@with_transaction
def complex_transaction(description, author, splits, valid_date=None):
    if valid_date is None:
        valid_date = date.today()
    objects = []
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_date=valid_date
    )
    objects.append(new_transaction)
    objects.extend(
        Split(amount=amount, account=account, transaction=new_transaction)
        for (account, amount) in splits
    )
    session.session.add_all(objects)


def transferred_amount(from_account, to_account, begin_date=None, end_date=None):
    """
    Determine how much has been transferred from one account to another in a
    given interval.

    A negative value indicates that more has been transferred from to_account
    to from_account than the other way round.

    The interval boundaries may be None, which indicates no lower and upper
    bound respectively.
    :param FinanceAccount from_account:
    :param FinanceAccount to_account:
    :param date|None begin_date: since when (inclusive)
    :param date|None end_date: till when (inclusive)
    :rtype: int
    """
    split1 = aliased(Split)
    split2 = aliased(Split)
    query = session.session.query(
        cast(func.sum(
            sign(split2.amount) *
            least(func.abs(split1.amount), func.abs(split2.amount))
        ), Integer)
    ).select_from(
        split1
    ).join(
        (split2, split1.transaction_id == split2.transaction_id)
    ).join(
        Transaction, split2.transaction_id == Transaction.id
    ).filter(
        split1.account == from_account,
        split2.account == to_account,
        sign(split1.amount) != sign(split2.amount)
    )
    if begin_date is not None and end_date is not None:
        query = query.filter(
            between(Transaction.valid_date, begin_date, end_date)
        )
    elif begin_date is not None:
        query = query.filter(Transaction.valid_date >= begin_date)
    elif end_date is not None:
        query = query.filter(Transaction.valid_date <= end_date)
    return query.scalar()


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


class CSVImportError(Exception):

    def __init__(self, message, cause=None):
        if cause is not None:
            message = message + u" caused by " + repr(cause)
        super(CSVImportError, self).__init__(message, cause)
        self.cause = cause


@with_transaction
def import_journal_csv(csv_file, import_time=None):
    if import_time is None:
        import_time = datetime.utcnow()

    # Convert to MT940Record and enumerate
    reader = csv.DictReader(csv_file, MT940_FIELDNAMES, dialect=MT940Dialect)
    records = enumerate(imap(lambda r: MT940Record(**r), reader), 1)
    # Skip first record (header)
    try:
        records.next()
    except StopIteration:
        raise CSVImportError(u"Leerer Datensatz.")

    session.session.add_all(imap(
        lambda r: process_record(r[0], r[1], import_time),
        reversed(list(records))
    ))


def remove_space_characters(field):
    """Remove every 28th character if it is a space character."""
    if field is None:
        return None
    characters = filter(
        lambda c: (c[0] + 1) % 28 != 0 or c[1] != u' ',
        enumerate(field)
    )
    return u"".join(map(lambda c: c[1], characters))


# Banks are using the original description field to store several subfields with
# SEPA. Subfields start with a four letter tag name and the plus sign, they
# are separated by space characters.
sepa_description_field_tags = (
    u'EREF', u'KREF', u'MREF', u'CRED', u'DEBT', u'SVWZ', u'ABWA', u'ABWE'
)
sepa_description_pattern = re.compile(r''.join(chain(
    ur'^',
    map(
        lambda tag: ur'(?:({0}\+.*?)(?: (?!$)|$))?'.format(tag),
        sepa_description_field_tags
    ),
    ur'$'
)), re.UNICODE)


def cleanup_description(description):
    match = sepa_description_pattern.match(description)
    if match is None:
        return description
    return u' '.join(map(
        remove_space_characters,
        filter(
            lambda g: g is not None,
            match.groups()
        )
    ))


def restore_record(record):
    string_buffer = cStringIO.StringIO()
    csv.DictWriter(
        string_buffer, MT940_FIELDNAMES, dialect=MT940Dialect
    ).writerow(record._asdict())
    restored_record = string_buffer.getvalue()
    string_buffer.close()
    return restored_record


def process_record(index, record, import_time):
    if record.currency != u"EUR":
        message = u"Nicht unterstützte Währung {0} in Datensatz {1}: {2}"
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.currency, index, raw_record)
        )
    try:
        journal = Journal.q.filter_by(
            account_number=record.our_account_number
        ).one()
    except NoResultFound as e:
        message = u"Kein Journal mit der Kontonummer {0} gefunden."
        raise CSVImportError(message.format(record.our_account_number), e)

    try:
        valid_date = datetime.strptime(record.valid_date, u"%d.%m.%y").date()
        transaction_date = (datetime
                            .strptime(record.transaction_date, u"%d.%m")
                            .date())
    except ValueError as e:
        message = u"Unbekanntes Datumsformat in Datensatz {0}: {1}"
        raw_record = restore_record(record)
        raise CSVImportError(message.format(index, raw_record), e)

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

def user_has_paid(user):
    # TODO check if user has paid
    return True


def get_typed_splits(splits):
    return izip_longest(
        ifilter(lambda s: s.amount > 0, splits),
        ifilter(lambda s: s.amount <= 0, splits)
    )
