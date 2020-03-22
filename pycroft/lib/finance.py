# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from abc import ABCMeta, abstractmethod
from collections import namedtuple
import csv
from datetime import datetime, date, timedelta
from decimal import Decimal
import difflib
from functools import partial
from itertools import chain, islice, starmap, tee, zip_longest
from io import StringIO
import operator
import re
from typing import Optional

from sqlalchemy import or_, and_, literal_column, literal, select, exists, not_, \
    text, DateTime
from sqlalchemy.orm import aliased, contains_eager, joinedload
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func, between, Integer, cast

from pycroft import config, model
from pycroft.helpers.i18n import deferred_gettext, gettext, Message
from pycroft.helpers.date import diff_month, last_day_of_month
from pycroft.helpers.utc import time_max, time_min
from pycroft.lib.logging import log_user_event
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.model import session
from pycroft.model.facilities import Room, Building
from pycroft.model.finance import (
    Account, BankAccount, BankAccountActivity, Split, Transaction, MembershipFee)
from pycroft.helpers.interval import (
    closed, single, Bound, Interval, IntervalSet, UnboundedInterval, closedopen)
from pycroft.model.functions import sign, least
from pycroft.model.property import CurrentProperty
from pycroft.model.session import with_transaction
from pycroft.model.types import Money
from pycroft.model.user import User, Membership, RoomHistoryEntry


def get_membership_fee_for_date(target_date):
    """
    Get the membership fee which contains a given target date.
    :param date target_date: The date for which a corresponding membership
    fee should be found.
    :rtype: MembershipFee
    :raises sqlalchemy.orm.exc.NoResultFound if no membership fee was found
    :raises sqlalchemy.orm.exc.MultipleResultsFound if multiple membership fees
    were found.
    """
    return MembershipFee.q.filter(
        between(target_date, MembershipFee.begins_on,
                MembershipFee.ends_on)
    ).one()


def get_last_applied_membership_fee():
    """
    Get the last applied membership fee.
    :rtype: MembershipFee
    """
    return MembershipFee.q.filter(
        MembershipFee.ends_on <= func.current_timestamp()) \
        .order_by(MembershipFee.ends_on.desc()).first()


def get_first_applied_membership_fee():
    """
    Get the first applied membership fee.
    :rtype: MembershipFee
    """
    return MembershipFee.q.order_by(
        MembershipFee.ends_on.desc()).first()


@with_transaction
def simple_transaction(description, debit_account, credit_account, amount,
                       author, valid_on=None, confirmed=True):
    """
    Posts a simple transaction.
    A simple transaction is a transaction that consists of exactly two splits,
    where one account is debited and another different account is credited with
    the same amount.
    The current system date will be used as transaction date, an optional valid
    date may be specified.
    :param unicode description: Description
    :param Account debit_account: Debit (germ. Soll) account.
    :param Account credit_account: Credit (germ. Haben) account
    :param Decimal amount: Amount in Eurocents
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
        valid_on=valid_on,
        confirmed=confirmed)
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
    return new_transaction


def transferred_amount(from_account, to_account, when=UnboundedInterval):
    """
    Determine how much has been transferred from one account to another in a
    given interval.

    A negative value indicates that more has been transferred from to_account
    to from_account than the other way round.

    The interval boundaries may be None, which indicates no lower and upper
    bound respectively.
    :param Account from_account: source account
    :param Account to_account: destination account
    :param Interval[date] when: Interval in which transactions became valid
    :rtype: int
    """
    split1 = aliased(Split)
    split2 = aliased(Split)
    query = session.session.query(
        cast(func.sum(
            sign(split2.amount) *
            least(func.abs(split1.amount), func.abs(split2.amount))
        ), Money)
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


membership_fee_description = deferred_gettext("Mitgliedsbeitrag {fee_name}")
@with_transaction
def post_transactions_for_membership_fee(membership_fee, processor,
                                         simulate=False):
    """
    Posts transactions (and splits) for users where the specified membership fee
    was not posted yet.

    User select: User -> Split (user account) -> Transaction -> Split (fee account)
                 Conditions: User has `membership_fee` property on
                             begins_on + booking_begin - 1 day or
                             begins_on + booking_end - 1 day
                             and no transaction exists on the user account int the fee timespan

    :param membership_fee: The membership fee which should be posted
    :param processor:
    :param simulate: Do not post any transactions, just return the affected users.
    :return: A list of name of all affected users
    """

    description = membership_fee_description.format(
        fee_name=membership_fee.name).to_json()

    split_user_account = Split.__table__.alias()
    split_fee_account = Split.__table__.alias()

    rhe_end = RoomHistoryEntry.__table__.alias()
    rhe_begin = RoomHistoryEntry.__table__.alias()

    fee_accounts = Account.q.join(Building).distinct(Account.id).all()
    fee_accounts_ids = set([acc.id for acc in fee_accounts] + [config.membership_fee_account_id])

    properties_beginning_timestamp = datetime.combine((membership_fee.begins_on
                                                       + membership_fee.booking_begin
                                                       - timedelta(1)),
                                                      time_min())

    properties_end_timestamp = datetime.combine((membership_fee.begins_on
                                                   + membership_fee.booking_end
                                                   - timedelta(1)),
                                                  time_max())

    # Select all users who fulfill the requirements for the fee in the fee timespan
    users = (select([User.id.label('id'),
                     User.name.label('name'),
                     User.account_id.label('account_id'),
                     # Select fee_account_id of the building or the default
                     # fee_account_id if user was not living in a room at booking time
                     func.coalesce(Building.fee_account_id,
                                   literal(config.membership_fee_account_id)).label('fee_account_id')])
             .select_from(User.__table__
                 # Join the users properties at `booking_begin`
                 .outerjoin(func.evaluate_properties(properties_beginning_timestamp)
                            .alias('properties_beginning'),
                            literal_column('properties_beginning.user_id') == User.id)
                 # Join the users properties at `booking_end`
                 .outerjoin(func.evaluate_properties(properties_end_timestamp)
                            .alias('properties_end'),
                            literal_column('properties_end.user_id') == User.id)
                 # Join RoomHistoryEntry, Room and Building of the user at membership_fee.ends_on
                 .outerjoin(rhe_end,
                            and_(rhe_end.c.user_id == User.id,
                                 # Only join RoomHistoryEntry that is relevant
                                 # on the fee interval end date
                                 literal(membership_fee.ends_on)
                                 .between(rhe_end.c.begins_at,
                                          func.coalesce(rhe_end.c.ends_at,
                                                        literal('infinity')
                                                        .cast(DateTime)))
                                 ))
                 # Join RoomHistoryEntry, Room and Building of the user at membership_fee.begins_on
                 # As second option if user moved out within the month
                 .outerjoin(rhe_begin,
                            and_(rhe_begin.c.user_id == User.id,
                                 # Only join RoomHistoryEntry that is relevant
                                 # on the fee interval begin date
                                 literal(membership_fee.begins_on)
                                 .between(rhe_begin.c.begins_at,
                                          func.coalesce(rhe_begin.c.ends_at,
                                                        literal('infinity')
                                                        .cast(DateTime)))
                                 ))
                 # Join with Room from membership_fee.ends_on if available,
                 # if not, join with the Room from membership_fee.begins_on
                 .outerjoin(Room, Room.id == func.coalesce(rhe_begin.c.room_id, rhe_end.c.room_id))
                 .outerjoin(Building, Building.id == Room.building_id)
            )
            # Check if a booking already exists on the user account in the fee timespan
            .where(not_(exists(select([None]).select_from(split_user_account
                    .join(Transaction, Transaction.id == split_user_account.c.transaction_id)
                    .join(split_fee_account, split_fee_account.c.transaction_id == Transaction.id)
                )
                .where(and_(split_user_account.c.account_id == User.account_id,
                            Transaction.valid_on.between(literal(membership_fee.begins_on),
                                                         literal(membership_fee.ends_on)),
                            split_fee_account.c.account_id.in_(fee_accounts_ids),
                            split_fee_account.c.id != split_user_account.c.id))
            )))
            # Only those users who had the `membership_fee` property on `booking_begin` or
            # `booking_end`
            .where(or_(and_(literal_column('properties_beginning.property_name') == 'membership_fee',
                            not_(literal_column('properties_beginning.denied'))),
                       and_(literal_column('properties_end.property_name') == 'membership_fee',
                            not_(literal_column('properties_end.denied')))))
            .distinct()
            .cte('membership_fee_users'))

    affected_users_raw = session.session.execute(select([users.c.id,
                                                         users.c.name,
                                                         users.c.fee_account_id])).fetchall()

    if not simulate:
        numbered_users = (select([users.c.id,
                                  users.c.fee_account_id.label('fee_account_id'),
                                  users.c.account_id,
                                  func.row_number().over().label('index')])
                          .select_from(users)
                          .cte("membership_fee_numbered_users"))

        transactions = (Transaction.__table__.insert()
             .from_select([Transaction.description,
                           Transaction.author_id,
                           Transaction.posted_at,
                           Transaction.valid_on,
                           Transaction.confirmed],
                          select([literal(description),
                                  literal(processor.id),
                                  func.current_timestamp(),
                                  literal(membership_fee.ends_on),
                                  True]).select_from(users))
             .returning(Transaction.id)
             .cte('membership_fee_transactions'))

        numbered_transactions = (select([transactions.c.id, func.row_number().over().label('index')])
             .select_from(transactions)
             .cte('membership_fee_numbered_transactions'))

        split_insert_fee_account = (Split.__table__.insert()
            .from_select([Split.amount, Split.account_id, Split.transaction_id],
                         select([literal(-membership_fee.regular_fee, type_=Money),
                                 numbered_users.c.fee_account_id,
                                 numbered_transactions.c.id])
                         .select_from(numbered_users.join(numbered_transactions,
                                                          numbered_transactions.c.index == numbered_users.c.index))
                         )
            .returning(Split.id)
            .cte('membership_fee_split_fee_account'))

        split_insert_user = (Split.__table__.insert().from_select(
            [Split.amount, Split.account_id, Split.transaction_id],
            select([literal(membership_fee.regular_fee, type_=Money),
                    numbered_users.c.account_id,
                    numbered_transactions.c.id])
            .select_from(numbered_users.join(numbered_transactions,
                                             numbered_transactions.c.index == numbered_users.c.index)))
            .returning(Split.id)
            .cte('membership_fee_split_user'))

        session.session.execute(select([]).select_from(split_insert_fee_account
                                                       .join(split_insert_user,
                                                             split_insert_user.c.id ==
                                                             split_insert_fee_account.c.id)))

    affected_users = [dict(user) for user in affected_users_raw]

    return affected_users


def diff(posted, computed, insert_only=False):
    sequence_matcher = difflib.SequenceMatcher(None, posted, computed)
    missing_postings = []
    erroneous_postings = []
    for tag, i1, i2, j1, j2 in sequence_matcher.get_opcodes():
        if 'replace' == tag:
            if insert_only:
                continue

            erroneous_postings.extend(islice(posted, i1, i2))
            missing_postings.extend(islice(computed, j1, j2))
        if 'delete' == tag:
            if insert_only:
                continue

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
    return IntervalSet(_to_date_interval(i) for i in intervals)


MT940_FIELDNAMES = [
    'our_account_number',
    'posted_on',
    'valid_on',
    'type',
    'reference',
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
            message = gettext(u"{0}\nCaused by:\n{1}").format(
                message, cause
            )
        self.cause = cause
        super(CSVImportError, self).__init__(message)


def is_ordered(iterable, relation=operator.le):
    """
    Check that an iterable is ordered with respect to a given relation.
    :param iterable[T] iterable: an iterable
    :param (T,T) -> bool op: a binary relation (i.e. a function that returns a bool)
    :return: True, if each element and its successor yield True under the given
    relation.
    :rtype: bool
    """
    a, b = tee(iterable)
    try:
        next(b)
    except StopIteration:
        # iterable is empty
        return True
    return all(relation(x, y) for x, y in zip(a, b))


@with_transaction
def import_bank_account_activities_csv(csv_file, expected_balance,
                                       imported_at=None):
    """
    Import bank account activities from a MT940 CSV file into the database.

    The new activities are merged with the activities that are already saved to
    the database.
    :param csv_file:
    :param expected_balance:
    :param imported_at:
    :return:
    """

    if imported_at is None:
        imported_at = session.utcnow()

    # Convert to MT940Record and enumerate
    reader = csv.reader(csv_file, dialect=MT940Dialect)
    records = enumerate((MT940Record._make(r) for r in reader), 1)
    try:
        # Skip first record (header)
        next(records)
        activities = tuple(
            process_record(index, record, imported_at=imported_at)
            for index, record in records)
    except StopIteration:
        raise CSVImportError(gettext(u"No data present."))
    except csv.Error as e:
        raise CSVImportError(gettext(u"Could not read CSV."), e)
    if not activities:
        raise CSVImportError(gettext(u"No data present."))
    if not is_ordered((a[8] for a in activities), operator.ge):
        raise CSVImportError(gettext(
            u"Transaction are not sorted according to transaction date in "
            u"descending order."))
    first_posted_on = activities[-1][8]
    balance = session.session.query(
        func.coalesce(func.sum(BankAccountActivity.amount), 0)
    ).filter(
        BankAccountActivity.posted_on < first_posted_on
    ).scalar()
    a = tuple(session.session.query(
        BankAccountActivity.amount, BankAccountActivity.bank_account_id,
        BankAccountActivity.reference, BankAccountActivity.reference,
        BankAccountActivity.other_account_number,
        BankAccountActivity.other_routing_number,
        BankAccountActivity.other_name, BankAccountActivity.imported_at,
        BankAccountActivity.posted_on, BankAccountActivity.valid_on
    ).filter(
        BankAccountActivity.posted_on >= first_posted_on)
    )
    b = tuple(reversed(activities))
    matcher = difflib.SequenceMatcher(a=a, b=b)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if 'equal' == tag:
            continue
        elif 'insert' == tag:
            balance += sum(a[0] for a in islice(activities, j1, j2))
            session.session.add_all(
                BankAccountActivity(
                    amount=e[0], bank_account_id=e[1], reference=e[3],
                    other_account_number=e[4],
                    other_routing_number=e[5], other_name=e[6],
                    imported_at=e[7], posted_on=e[8], valid_on=e[9]
                ) for e in islice(activities, j1, j2)
            )
        elif 'delete' == tag:
            continue
        elif 'replace' == tag:
            raise CSVImportError(
                gettext(u"Import conflict:\n"
                        u"Database bank account activities:\n{0}\n"
                        u"File bank account activities:\n{1}").format(
                    u'\n'.join(str(x) for x in islice(activities, i1, i2)),
                    u'\n'.join(str(x) for x in islice(activities, j1, j2))))
        else:
            raise AssertionError()
    if balance != expected_balance:
        message = gettext(u"Balance after does not equal expected balance: "
                          u"{0} != {1}.")
        raise CSVImportError(message.format(balance, expected_balance))


def remove_space_characters(field):
    """Remove every 28th character if it is a space character."""
    if field is None:
        return None
    return u"".join(c for i, c in enumerate(field) if i % 28 != 27 or c != u' ')


# Banks are using the original reference field to store several subfields with
# SEPA. Subfields start with a four letter tag name and the plus sign, they
# are separated by space characters.
sepa_description_field_tags = (
    u'EREF', u'KREF', u'MREF', u'CRED', u'DEBT', u'SVWZ', u'ABWA', u'ABWE'
)
sepa_description_pattern = re.compile(''.join(chain(
    '^',
    [r'(?:({0}\+.*?)(?: (?!$)|$))?'.format(tag)
     for tag in sepa_description_field_tags],
    '$'
)), re.UNICODE)


def cleanup_description(description):
    match = sepa_description_pattern.match(description)
    if match is None:
        return description
    return u' '.join(remove_space_characters(f) for f in match.groups() if f is not None)


def restore_record(record):
    string_buffer = StringIO()
    csv.DictWriter(
        string_buffer, MT940_FIELDNAMES, dialect=MT940Dialect
    ).writerow(record._asdict())
    restored_record = string_buffer.getvalue()
    string_buffer.close()
    return restored_record


def process_record(index, record, imported_at):
    if record.currency != u"EUR":
        message = gettext(u"Unsupported currency {0}. Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(message.format(record.currency, index, raw_record))
    try:
        bank_account = BankAccount.q.filter_by(
            account_number=record.our_account_number
        ).one()
    except NoResultFound as e:
        message = gettext(u"No bank account with account number {0}. "
                          u"Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.our_account_number, index, raw_record), e)

    try:
        valid_on = datetime.strptime(record.valid_on, u"%d.%m.%y").date()
        posted_on = datetime.strptime(record.posted_on, u"%d.%m.%y").date()
    except ValueError as e:
        message = gettext(u"Illegal date format. Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(message.format(index, raw_record), e)

    try:
        amount = Decimal(record.amount.replace(u",", u"."))
    except ValueError as e:
        message = gettext(u"Illegal value format {0}. Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.amount, index, raw_record), e)

    return (amount, bank_account.id, cleanup_description(record.reference),
            record.reference, record.other_account_number,
            record.other_routing_number, record.other_name, imported_at,
            posted_on, valid_on)


def user_has_paid(user):
    return user.account.balance <= 0


def get_typed_splits(splits):
    splits = sorted(splits, key=lambda s: s.transaction.posted_at, reverse=True)
    return zip_longest(
        (s for s in splits if s.amount >= 0),
        (s for s in splits if s.amount < 0),
    )


def get_transaction_type(transaction):

    credited = [split.account for split in transaction.splits if split.amount>0]
    debited = [split.account for split in transaction.splits if split.amount<0]

    cd_accs = (credited, debited)
    # all involved accounts have the same type:
    if all(all(a.type == accs[0].type for a in accs) for accs in cd_accs)\
            and all(len(accs)>0 for accs in cd_accs):
        return (cd_accs[0][0].type, cd_accs[1][0].type)


@with_transaction
def end_payment_in_default_memberships():
    processor = User.q.get(0)

    users = User.q.join(User.current_properties) \
                .filter(CurrentProperty.property_name == 'payment_in_default') \
                .join(Account).filter(Account.balance <= 0).all()

    for user in users:
        if user.member_of(config.payment_in_default_group):
            remove_member_of(user, config.payment_in_default_group, processor,
                             closedopen(session.utcnow(), None))

    return users


def get_users_with_payment_in_default():
    # Add memberships and end "member" membership if threshold met
    users = User.q.join(User.current_properties) \
        .filter(CurrentProperty.property_name == 'membership_fee') \
        .join(Account).filter(Account.balance > 0).all()

    users_pid_membership = set()
    users_membership_terminated = set()

    ts_now = session.utcnow()
    for user in users:
        in_default_days = user.account.in_default_days

        try:
            fee_date = ts_now - timedelta(days=in_default_days)

            # datetime not working as datetime type
            fee = get_membership_fee_for_date(str(fee_date))
        except NoResultFound:
            fee = get_last_applied_membership_fee()

        if fee is None:
            raise ValueError("No fee found")

        if in_default_days >= fee.payment_deadline.days:
            # Skip user if the payment in default group membership was terminated within the last week
            last_pid_membership = Membership.q.filter(Membership.user_id == user.id).filter(
                Membership.group_id == config.payment_in_default_group.id).order_by(Membership.ends_at.desc()).first()

            if last_pid_membership is not None:
                if last_pid_membership.ends_at is not None and \
                        last_pid_membership.ends_at >= ts_now - timedelta(days=7):
                    continue

            if not user.has_property('payment_in_default'):
                # Add user to new payment in default list
                users_pid_membership.add(user)

        if in_default_days >= fee.payment_deadline_final.days:
            # Add user to terminated memberships
            users_membership_terminated.add(user)

    users_membership_terminated.difference_update(users_pid_membership)

    return users_pid_membership, users_membership_terminated


@with_transaction
def take_actions_for_payment_in_default_users(users_pid_membership,
                                              users_membership_terminated,
                                              processor):
    ts_now = session.utcnow()

    for user in users_pid_membership:
        if not user.member_of(config.payment_in_default_group):
            make_member_of(user, config.payment_in_default_group,
                           processor, closed(ts_now, None))

    from pycroft.lib.user import move_out

    for user in users_membership_terminated:
        if user.member_of(config.member_group):
            move_out(user, "Zahlungsrückstand", processor, ts_now, True)

            log_user_event("Mitgliedschaftsende wegen Zahlungsrückstand.",
                           processor, user)


def process_transactions(bank_account, statement):
    transactions = []  # new transactions which would be imported
    old_transactions = []  # transactions which are already imported
    doubtful_transactions = [] # transactions which may be changed by the bank because they are to new

    for transaction in statement:
        iban = transaction.data.get('applicant_iban', '')
        if iban is None: iban = ''
        bic = transaction.data.get('applicant_bin', '')
        if bic is None: bic = ''
        other_name = transaction.data.get('applicant_name', '')
        if other_name is None: other_name = ''
        purpose = transaction.data.get('purpose', '')
        if purpose is None: purpose = ''
        if 'end_to_end_reference' in transaction.data and \
                transaction.data['end_to_end_reference'] is not None:
            purpose = purpose + ' EREF+' + transaction.data['end_to_end_reference']
        new_activity = BankAccountActivity(
            bank_account_id=bank_account.id,
            amount=transaction.data['amount'].amount,
            reference=purpose,
            other_account_number=iban,
            other_routing_number=bic,
            other_name=other_name,
            imported_at=session.utcnow(),
            posted_on=transaction.data['guessed_entry_date'],
            valid_on=transaction.data['date'],
        )
        if new_activity.posted_on >= date.today():
            doubtful_transactions.append(new_activity)
        elif BankAccountActivity.q.filter(and_(
                BankAccountActivity.bank_account_id ==
                new_activity.bank_account_id,
                BankAccountActivity.amount == new_activity.amount,
                BankAccountActivity.reference == new_activity.reference,
                BankAccountActivity.other_account_number ==
                new_activity.other_account_number,
                BankAccountActivity.other_routing_number ==
                new_activity.other_routing_number,
                BankAccountActivity.other_name == new_activity.other_name,
                BankAccountActivity.posted_on == new_activity.posted_on,
                BankAccountActivity.valid_on == new_activity.valid_on
        )).first() is None:
            transactions.append(new_activity)
        else:
            old_transactions.append(new_activity)

    return (transactions, old_transactions, doubtful_transactions)


def build_transactions_query(account, search=None, sort_by='valid_on', sort_order=None,
                             offset=None, limit=None, positive=None, eagerload=False):
    """Build a query returning the Splits for a finance account

    :param Account account: The finance Account to filter by
    :param str search: The string to be included, insensitive
    :param str sort_by: The column to sort by.  Must be a column of
        :cls:`Transaction` or :cls:`Split`.
    :param str sort_order: Trigger descending sort order if the value
        is ``'desc'``.  See also the effect of :attr:`positive`.
    :param int offset:
    :param int limit:
    :param bool positive: if positive is set to ``True``, only get
        splits with amount ≥ 0, and amount < 0 if ``False``.  In the
        latter case, the effect of the :attr:`sort_order` parameter is
        being reversed.
    :param bool eagerload: Eagerly load involved transactions.

    :returns: The prepared SQLAlchemy query

    :rtype: Query
    """
    query = Split.q.join(Transaction).filter(Split.account == account)

    if not (sort_by in Transaction.__table__.columns
            or sort_by in Split.__table__.columns):
        sort_by = "valid_on"

    descending = (sort_order == "desc") ^ (positive == False)
    ordering = sort_by+" desc" if descending else sort_by
    if search:
        query = query.filter(Transaction.description.ilike('%{}%'.format(search)))

    if positive is not None:
        if positive:
            query = query.filter(Split.amount >= 0)
        else:
            query = query.filter(Split.amount < 0)

    query = query.order_by(text(ordering)).offset(offset).limit(limit)

    if eagerload:
        query = query.options(contains_eager(Split.transaction))

    return query

def match_activities():
    """Get a dict of all unmatched transactions and a user they should be matched with

    :param BankAccount bank_account: The BankAccount to get the unmatched transactions from

    :returns: Dictionary with transaction and user
    :rtype: Dict
    """
    from pycroft.lib.user import check_user_id
    matching = {}
    activity_q = (BankAccountActivity.q
                  .options(joinedload(BankAccountActivity.bank_account))
                  .filter(BankAccountActivity.transaction_id == None))

    for activity in activity_q.all():
        # search for user-ID
        user = None
        reference = activity.reference.replace('AWV-MELDEPFLICHT BEACHTENHOTLINE BUNDESBANK.(0800) 1234-111', '')
        search = re.search(r"(([\d]{4,6} ?[-/?:,+.]? ?[\d]{1,2})|(gerok38|GEROK38|Gerok38)/(([a-zA-Z]*\s?)+))", reference)

        if search is None:
            search = re.search(r"(([\d]{4,6} ?[-/?:,+.]? ?[\d]{1,2}))", reference.replace(' ', ''))

        if search:
            if activity.reference.lower().startswith('gerok38'):
                user = User.q.filter(func.lower(User.name)==func.lower(search.group(4))).first()
            else:
                for group in search.groups():
                    try:
                        uid = group.replace(' ', '').replace('/', '-') \
                            .replace('?', '-').replace(':', '-').replace(',', '-') \
                            .replace('+', '-').replace('.', '-')
                        if uid[-2] is not '-' and uid[-3] is not '-':
                            # interpret as type 2 UID with missing -
                            uid = uid[:-2] + '-' + uid[-2:]

                        if check_user_id(uid):
                            uid = uid.split("-")[0]
                            user = User.q.get(uid)
                            break
                    except AttributeError:
                        user = None
            if user:
                matching.update({activity: user})

    return matching


@with_transaction
def transaction_delete(transaction):
    if transaction.confirmed:
        raise ValueError("transaction already confirmed")

    session.session.delete(transaction)


@with_transaction
def transaction_confirm(transaction):
    if transaction.confirmed:
        raise ValueError("transaction already confirmed")

    transaction.confirmed = True


def fee_from_valid_date(valid_on: date, account: Account) -> Optional[Split]:
    """If existent, get the membership fee split for a given date"""
    return (
        Split.q
             .filter_by(account=account)
             .join(Transaction)
             .filter(Split.amount > 0)
             .filter(Transaction.valid_on == valid_on)
    ).first()


def estimate_balance(user, end_date):
    """
    :param user: The member
    :param end_date: Date of the end of the membership
    :return: Estimated balance at the end_date
    """

    now = session.utcnow().date()

    # Use tomorrow in case that it is the last of the month, the fee for the
    # current month will be added later
    tomorrow = now + timedelta(1)

    last_fee = MembershipFee.q.order_by(MembershipFee.ends_on.desc()).first()

    if last_fee is None:
        raise ValueError("no fee information available")

    # Bring end_date to previous month if the end_date is in grace period
    end_date_justified = end_date - timedelta(last_fee.booking_begin.days - 1)

    months_to_pay = diff_month(end_date_justified, tomorrow)

    # If the user has to pay a fee for the current month
    if user.has_property('membership_fee',
                         single(tomorrow.replace(day=last_fee.booking_end.days))):
        months_to_pay += 1

    # If there was no fee booked yet for the last month and the user has to pay
    # a fee for the last month, increment months_to_pay
    last_month_last = tomorrow.replace(day=1) - timedelta(1)
    last_month_fee_outstanding = (
        fee_from_valid_date(last_month_last, user.account) is None
    )

    if last_month_fee_outstanding:
        had_to_pay_last_month = user.has_property(
            'membership_fee',
            single(last_month_last.replace(day=last_fee.booking_end.days))
        )
        if had_to_pay_last_month:
            months_to_pay += 1

    # If there is already a fee booked for this month, decrement months_to_pay
    this_month_fee_outstanding = (
        fee_from_valid_date(last_day_of_month(tomorrow), user.account) is None
    )
    if not this_month_fee_outstanding:
        months_to_pay -= 1

    return (-user.account.balance) - (months_to_pay * last_fee.regular_fee)


def get_pid_csv():
    users_pid_membership, users_membership_terminated = get_users_with_payment_in_default()

    f = StringIO()

    writer = csv.writer(f)
    writer.writerow(('email', 'name', 'balance'))
    writer.writerows(("{}@wh2.tu-dresden.de".format(u.login), u.name, str(-u.account.balance)) for u in users_pid_membership)

    return f.getvalue()
