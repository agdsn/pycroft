# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from abc import ABCMeta, abstractmethod
from collections import namedtuple
import cStringIO
import csv
from datetime import datetime, date, timedelta
import difflib
from itertools import chain, ifilter, imap, izip_longest, tee, izip, islice
import operator
import re

from sqlalchemy import or_
from sqlalchemy.orm import aliased
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func, between, Integer, cast

from pycroft import config
from pycroft.model import session
from pycroft.model.finance import (
    Semester, FinanceAccount, Transaction, Split,
    Journal, JournalEntry)
from pycroft.helpers.interval import (
    closed, single, Bound, Interval, IntervalSet, UnboundedInterval)
from pycroft.model.functions import sign, least
from pycroft.model.session import with_transaction
from pycroft.model.user import User


def get_semesters(when=UnboundedInterval):
    """

    :param when:
    :return:
    """
    criteria = []
    if when.begin is not None:
        criteria.append(or_(
            when.begin <= Semester.begins_on,
            between(when.begin, Semester.begins_on, Semester.ends_on)
        ))
    if when.end is not None:
        criteria.append(or_(
            when.end >= Semester.ends_on,
            between(when.end, Semester.begins_on, Semester.ends_on)
        ))
    return Semester.q.filter(*criteria).order_by(Semester.begins_on)


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
        between(target_date, Semester.begins_on, Semester.ends_on)
    ).one()


def get_current_semester():
    """
    Get the current semester.
    :rtype: Semester
    """
    return get_semester_for_date(datetime.utcnow().date())


@with_transaction
def simple_transaction(description, debit_account, credit_account, amount,
                       author, valid_on=None):
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
    :param date valid_on: Date, when the transaction should be valid. Current
    database date, if omitted.
    :type valid_on: date or None
    :rtype: Transaction
    """
    if valid_on is None:
        valid_on = session.utcnow().date()
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_on=valid_on)
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

    fees = [
        RegistrationFee(FinanceAccount.q.get(
            config["finance"]["registration_fee_account_id"]
        )),
        SemesterFee(FinanceAccount.q.get(
            config["finance"]["semester_fee_account_id"]
        )),
    ]
    # Initial bookings
    post_fees([new_user], fees, processor)


@with_transaction
def complex_transaction(description, author, splits, valid_on=None):
    if valid_on is None:
        valid_on = session.utcnow().date()
    objects = []
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_on=valid_on
    )
    objects.append(new_transaction)
    objects.extend(
        Split(amount=amount, account=account, transaction=new_transaction)
        for (account, amount) in splits
    )
    session.session.add_all(objects)


def transferred_amount(from_account, to_account, when=UnboundedInterval):
    """
    Determine how much has been transferred from one account to another in a
    given interval.

    A negative value indicates that more has been transferred from to_account
    to from_account than the other way round.

    The interval boundaries may be None, which indicates no lower and upper
    bound respectively.
    :param FinanceAccount from_account:
    :param FinanceAccount to_account:
    :param Interval[date] when: Interval in which transactions became valid
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
    if not when.unbounded:
        query = query.filter(
            between(Transaction.valid_on, when.begin, when.end)
        )
    elif when.begin is not None:
        query = query.filter(Transaction.valid_on >= when.begin)
    elif when.end is not None:
        query = query.filter(Transaction.valid_on <= when.end)
    return query.scalar()


@with_transaction
def post_fees(users, fees, processor):
    """
    Calculate the given fees for all given user accounts from scratch and post
    them if they have not already been posted and correct erroneous postings.
    :param iterable[User] users:
    :param iterable[Fee] fees:
    :param User processor:
    """
    adjustment_description = config["finance"]["adjustment_description"]
    for user in users:
        for fee in fees:
            computed_debts = fee.compute(user)
            posted_transactions = fee.get_posted_transactions(user).all()
            posted_credits = tuple(t for t in posted_transactions if t.amount > 0)
            posted_corrections = tuple(t for t in posted_transactions if t.amount < 0)
            missing_debts, erroneous_debts = diff(posted_credits, computed_debts)
            computed_adjustments = tuple(
                ((adjustment_description.format(
                    original_description=description,
                    original_valid_on=valid_on)),
                 valid_on, -amount)
                for description, valid_on, amount in erroneous_debts)
            missing_adjustments, erroneous_adjustments = diff(
                posted_corrections, computed_adjustments
            )
            missing_postings = chain(missing_debts, missing_adjustments)
            today = session.utcnow().date()
            for description, valid_on, amount in missing_postings:
                if valid_on <= today:
                    simple_transaction(
                        description, fee.account, user.finance_account,
                        amount, processor, valid_on)


def diff(posted, computed):
    sequence_matcher = difflib.SequenceMatcher(None, posted, computed)
    missing_postings = []
    erroneous_postings = []
    for tag, i1, i2, j1, j2 in sequence_matcher.get_opcodes():
        if 'replace' == tag:
            erroneous_postings.extend(islice(posted, i1, i2))
            missing_postings.extend(islice(computed, j1, j2))
        if 'delete' == tag:
            erroneous_postings.extend(islice(posted, i1, i2))
        if 'insert' == tag:
            missing_postings.extend(islice(computed, j1, j2))
    return missing_postings, erroneous_postings


def _to_date_interval(interval):
    """
    :param Interval[datetime] interval:
    :rtype: Interval[date]
    """
    if interval.lower_bound.unbounded:
        lower_bound = interval.lower_bound
    else:
        lower_bound = Bound(interval.lower_bound.value.date(),
                            interval.lower_bound.closed)
    if interval.upper_bound.unbounded:
        upper_bound = interval.upper_bound
    else:
        upper_bound = Bound(interval.upper_bound.value.date(),
                            interval.upper_bound.closed)
    return Interval(lower_bound, upper_bound)


def _to_date_intervals(intervals):
    """
    :param IntervalSet[datetime] intervals:
    :rtype: IntervalSet[date]
    """
    return IntervalSet(imap(_to_date_interval, intervals))


class Fee(object):
    """
    Fees must be idempotent, that means if a fee has been applied to a user,
    another application must not result in any change. This property allows
    all the fee to be calculated for all times instead of just the current
    semester or the current day and makes the calculation independent of system
    time it was running.
    """
    __metaclass__ = ABCMeta

    validity_period = UnboundedInterval

    def __init__(self, account):
        self.account = account
        self.session = session.session

    def get_posted_transactions(self, user):
        """
        Get all fee transactions that have already been posted to the user's
        finance account.
        :param User user:
        :return:
        :rtype: list[(unicode, date, int)]
        """
        split1 = aliased(Split)
        split2 = aliased(Split)
        transactions = self.session.query(
            Transaction.description, Transaction.valid_on, split1.amount
        ).select_from(Transaction).join(
            (split1, split1.transaction_id == Transaction.id),
            (split2, split2.transaction_id == Transaction.id)
        ).filter(
            split1.account_id == user.finance_account_id,
            split2.account_id == self.account.id
        ).order_by(Transaction.valid_on)
        return transactions

    @abstractmethod
    def compute(self, user):
        """
        Compute all debts the user owes us for this particular fee. Debts must
        be in ascending order of valid_on.

        :param User user:
        :rtype: list[(unicode, date, int)]
        """
        pass


class RegistrationFee(Fee):
    def compute(self, user):
        description = config['finance']['registration_fee_description']
        when = single(user.registered_at)
        if user.has_property("registration_fee", when):
            try:
                semester = get_semester_for_date(user.registered_at.date())
            except NoResultFound:
                return []
            fee = semester.registration_fee
            if fee > 0:
                return [(description, user.registered_at.date(), fee)]
        return []


class SemesterFee(Fee):
    def compute(self, user):
        liability_intervals = _to_date_intervals(
            user.property_intervals("semester_fee")
        )
        if not liability_intervals:
            return []
        semesters = get_semesters(closed(
            liability_intervals[0].begin,
            liability_intervals[-1].end
        ))
        away_intervals = _to_date_intervals(user.property_intervals("away"))
        description = config["finance"]["semester_fee_description"]
        debts = []
        # Compute semester fee for each semester the user is liable to pay it
        for semester in semesters:
            semester_interval = closed(semester.begins_on, semester.ends_on)
            liable_in_semester = liability_intervals & semester_interval
            if not liable_in_semester:
                continue
            if liable_in_semester.length <= semester.grace_period:
                continue
            away_in_semester = away_intervals & semester_interval
            present_in_semester = liable_in_semester - away_in_semester
            valid_on = liable_in_semester[0].begin
            if present_in_semester.length <= semester.reduced_semester_fee_threshold:
                amount = semester.reduced_semester_fee
            else:
                amount = semester.regular_semester_fee
            if amount > 0:
                debts.append((
                    description.format(semester=semester.name),
                    valid_on, amount))
        return debts


class LateFee(Fee):
    def __init__(self, account, calculate_until):
        """
        :param date calculate_until: Date up until late fees are calculated;
        usually the date of the last bank import
        :param int allowed_overdraft: Amount of overdraft which does not result
        in an late fee being charged.
        :param payment_deadline: Timedelta after which a payment is late
        """
        super(LateFee, self).__init__(account)
        self.calculate_until = calculate_until

    def non_late_fee_transactions(self, user):
        split1 = aliased(Split)
        split2 = aliased(Split)
        return self.session.query(
            Transaction.valid_on, (-func.sum(split2.amount)).label("debt")
        ).select_from(Transaction).join(
            (split1, split1.transaction_id == Transaction.id),
            (split2, split2.transaction_id == Transaction.id)
        ).filter(
            split1.account_id == user.finance_account_id,
            split2.account_id != user.finance_account_id,
            split2.account_id != self.account.id
        ).group_by(
            Transaction.id, Transaction.valid_on
        ).order_by(Transaction.valid_on)

    @staticmethod
    def running_totals(transactions):
        balance = 0
        last_credit = transactions[0][0]
        for valid_on, amount in transactions:
            if amount > 0:
                last_credit = valid_on
            else:
                delta = valid_on - last_credit
                yield last_credit, balance, delta
            balance += amount

    def compute(self, user):
        # Note: User finance accounts are assets accounts from our perspective,
        # that means their balance is positive, if the user owes us money
        transactions = self.non_late_fee_transactions(user).all()
        # Add a pseudo transaction on the day until late fees should be
        # calculated
        transactions.append((self.calculate_until, 0))
        liability_intervals = _to_date_intervals(
            user.property_intervals("late_fee")
        )
        description = config["finance"]["late_fee_description"]
        debts = []
        for last_credit, balance, delta in self.running_totals(transactions):
            semester = get_semester_for_date(last_credit)
            if (balance <= semester.allowed_overdraft or
                    delta <= semester.payment_deadline):
                continue
            valid_on = last_credit + semester.payment_deadline + timedelta(days=1)
            amount = semester.late_fee
            if liability_intervals & single(valid_on) and amount > 0:
                debts.append((
                    description.format(original_valid_on=last_credit),
                    amount, valid_on
                ))
        return debts


MT940_FIELDNAMES = [
    'our_account_number',
    'posted_at',
    'valid_on',
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
            message = u"{0}\nUrsprünglicher Fehler:\n{1}".format(
                message, cause
            )
        self.cause = cause
        super(CSVImportError, self).__init__(message)


def descending_transaction_dates(entries):
    a, b = tee(imap(operator.itemgetter(8), entries))
    next(b)
    return all(imap(lambda p: p[0] >= p[1], izip(a, b)))


@with_transaction
def import_journal_csv(csv_file, expected_balance, import_time=None):
    if import_time is None:
        import_time = session.utcnow()

    # Convert to MT940Record and enumerate
    reader = csv.reader(csv_file, dialect=MT940Dialect)
    records = enumerate(imap(MT940Record._make, reader), 1)
    try:
        # Skip first record (header)
        next(records)
        entries = tuple(imap(lambda r: process_record(r[0], r[1], import_time),
                             records))
    except StopIteration:
        raise CSVImportError(u"Leerer Datensatz.")
    except csv.Error as e:
        raise CSVImportError(u"Fehler beim Lesen der CSV-Daten.", e)
    if not entries:
        raise CSVImportError(u"Leerer Datensatz.")
    if not descending_transaction_dates(entries):
        raise CSVImportError(u"Buchungen nicht absteigend nach Buchungsdatum geordnet.")
    first_posted_at = entries[-1][8]
    balance = session.session.query(
        func.coalesce(func.sum(JournalEntry.amount), 0)
    ).filter(
        JournalEntry.posted_at < first_posted_at).scalar()
    a = tuple(session.session.query(
        JournalEntry.amount, JournalEntry.journal_id, JournalEntry.description,
        JournalEntry.original_description, JournalEntry.other_account_number,
        JournalEntry.other_routing_number, JournalEntry.other_name,
        JournalEntry.import_time, JournalEntry.posted_at,
        JournalEntry.valid_on
    ).filter(
        JournalEntry.posted_at >= first_posted_at))
    b = tuple(reversed(entries))
    matcher = difflib.SequenceMatcher(None, a, b)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if 'equal' == tag:
            continue
        elif 'insert' == tag:
            balance += sum(imap(operator.itemgetter(0),
                                islice(entries, j1, j2)))
            session.session.add_all(imap(
                lambda e: JournalEntry(
                    amount=e[0], journal_id=e[1], description=e[2],
                    original_description=e[3], other_account_number=e[4],
                    other_routing_number=e[5], other_name=e[6],
                    import_time=e[7], posted_at=e[8], valid_on=e[9]),
                islice(entries, j1, j2)))
        elif 'delete' == tag:
            continue
        elif 'replace':
            raise CSVImportError(u"Konflikt beim Import.")
        else:
            raise AssertionError()
    if balance != expected_balance:
        message = u"Summe nach Import entspricht nicht der erwarteten Summe: " \
                  u"{0} != {1}."
        raise CSVImportError(message.format(balance, expected_balance))


def remove_space_characters(field):
    """Remove every 28th character if it is a space character."""
    if field is None:
        return None
    characters = filter(
        lambda c: c[0] % 28 != 27 or c[1] != u' ',
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


def process_record(index, record, imported_at):
    if record.currency != u"EUR":
        message = u"Nicht unterstützte Währung {0} in Datensatz {1}: {2}"
        raw_record = restore_record(record)
        raise CSVImportError(message.format(record.currency, index, raw_record))
    try:
        journal = Journal.q.filter_by(
            account_number=record.our_account_number
        ).one()
    except NoResultFound as e:
        message = u"Kein Journal mit der Kontonummer {0} in Datensatz {1} " \
                  u"gefunden: {2}"
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.our_account_number, index, raw_record), e)

    try:
        valid_on = datetime.strptime(record.valid_on, u"%d.%m.%y").date()
        posted_at = datetime.strptime(record.posted_at, u"%d.%m.%y").date()
    except ValueError as e:
        message = u"Falsches Datumsformat in Datensatz {0}: {1}"
        raw_record = restore_record(record)
        raise CSVImportError(message.format(index, raw_record), e)

    try:
        amount = int(record.amount.replace(u",", u""))
    except ValueError as e:
        message = u"Falsches Betragsformat {0} in Datensatz {1}: {2}"
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.amount, index, raw_record), e)
    try:
        description = record.description.decode('utf8')
        other_name = record.other_name.decode('utf8')
    except UnicodeDecodeError as e:
        raise CSVImportError(u"Fehler beim Dekodieren aus UTF-8", e)
    return (amount, journal.id, cleanup_description(description),
            description, record.other_account_number,
            record.other_routing_number, other_name, imported_at,
            posted_at, valid_on)


def user_has_paid(user):
    return sum(split.amount for split in (Split.q.filter_by(
        account_id=user.finance_account.id
    ))) >= 0


def get_typed_splits(splits):
    return izip_longest(
        ifilter(lambda s: s.amount > 0, splits),
        ifilter(lambda s: s.amount <= 0, splits)
    )
