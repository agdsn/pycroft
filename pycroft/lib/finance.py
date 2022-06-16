# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import csv
import difflib
import logging
import operator
import re
import typing
from datetime import datetime, date, timedelta
from decimal import Decimal
from io import StringIO
from itertools import chain, islice, tee, zip_longest
from typing import Callable, TypeVar, NamedTuple

from sqlalchemy import func, between, cast
from sqlalchemy import or_, and_, literal, select, exists, not_, \
    text, future
from sqlalchemy.orm import aliased, contains_eager, joinedload, Session
from sqlalchemy.orm.exc import NoResultFound

from pycroft import config
from pycroft.helpers.date import diff_month, last_day_of_month
from pycroft.helpers.i18n import deferred_gettext, gettext
from pycroft.helpers.interval import (
    closed, Bound, Interval, IntervalSet, UnboundedInterval, closedopen)
from pycroft.helpers.utc import with_min_time, with_max_time
from pycroft.lib.exc import PycroftLibException
from pycroft.lib.logging import log_user_event, log_event
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.model import session
from pycroft.model.base import ModelBase
from pycroft.model.facilities import Room, Building
from pycroft.model.finance import (
    Account, BankAccount, BankAccountActivity, Split, Transaction,
    MembershipFee)
from pycroft.model.functions import sign, least
from pycroft.model.property import CurrentProperty, evaluate_properties
from pycroft.model.session import with_transaction, utcnow
from pycroft.model.types import Money
from pycroft.model.user import User, Membership, RoomHistoryEntry

logger = logging.getLogger('pycroft.lib.finance')


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
    :param confirmed: If transaction should be created as confirmed
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
def complex_transaction(description, author, splits, valid_on=None, confirmed=True):
    if valid_on is None:
        valid_on = session.utcnow().date()
    objects: list[ModelBase] = []
    new_transaction = Transaction(
        description=description,
        author=author,
        valid_on=valid_on,
        confirmed=confirmed,
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
        split2, split1.transaction_id == split2.transaction_id
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


# this „2.0-style select“ is only completely supported on a typing level when we have the v2.0
#  typing infrastructure (post-mypy plugin).
#  See https://docs.sqlalchemy.org/en/14/orm/extensions/mypy.html#mypy-pep-484-support-for-orm-mappings
# See also #562
@typing.no_type_check
def users_eligible_for_fee_query(membership_fee):
    split_user_account = Split.__table__.alias()
    split_fee_account = Split.__table__.alias()

    rhe_end = RoomHistoryEntry.__table__.alias()
    rhe_begin = RoomHistoryEntry.__table__.alias()

    fee_accounts = Account.q.join(Building).distinct(Account.id).all()
    fee_accounts_ids = set([acc.id for acc in fee_accounts] + [config.membership_fee_account_id])

    properties_beginning_timestamp = with_min_time(
        membership_fee.begins_on
        + membership_fee.booking_begin
        - timedelta(1)
    )
    properties_end_timestamp = with_max_time(
        membership_fee.begins_on
        + membership_fee.booking_end
        - timedelta(1)
    )

    begin_tstz = with_min_time(membership_fee.begins_on)
    end_tstz = with_max_time(membership_fee.ends_on)

    fee_prop_beginning = evaluate_properties(properties_beginning_timestamp, name='fee_prop_beg')
    fee_prop_end = evaluate_properties(properties_end_timestamp, name='fee_prop_end')

    return (future.select(User.id.label('id'),
                     User.name.label('name'),
                     User.account_id.label('account_id'),
                     # Select fee_account_id of the building or the default
                     # fee_account_id if user was not living in a room at booking time
                     func.coalesce(Building.fee_account_id,
                                   literal(config.membership_fee_account_id)).label('fee_account_id'))
             .select_from(User.__table__
                 # The first two joins are there for filtering reasons (does this user have to pay?)
                 # ----
                 # `membership_fee` flag on booking_begin, if existent
                 .outerjoin(fee_prop_beginning,
                            and_(fee_prop_beginning.c.user_id == User.id,
                                 fee_prop_beginning.c.property_name == 'membership_fee',
                                 not_(fee_prop_beginning.c.denied)))
                 # `membership_fee` flag on booking_end, if existent
                 .outerjoin(fee_prop_end,
                            and_(fee_prop_end.c.user_id == User.id,
                                 fee_prop_end.c.property_name == 'membership_fee',
                                 not_(fee_prop_end.c.denied)))

                 # The following joins are there to get a meaningful `account_id` for the user
                 # ----
                 # Join RoomHistoryEntry, Room and Building of the user at membership_fee.ends_on
                 .outerjoin(rhe_end,
                            and_(rhe_end.c.user_id == User.id,
                                 # Only join RoomHistoryEntry that is relevant
                                 # on the fee interval end date
                                 literal(end_tstz).op("<@")(rhe_end.c.active_during)))
                 # Join RoomHistoryEntry, Room and Building of the user at membership_fee.begins_on
                 # As second option if user moved out within the month
                 .outerjoin(rhe_begin,
                            and_(rhe_begin.c.user_id == User.id,
                                 # Only join RoomHistoryEntry that is relevant
                                 # on the fee interval end date
                                 literal(begin_tstz).op("<@")(rhe_begin.c.active_during)))
                 # Join with Room from membership_fee.ends_on if available,
                 # if not, join with the Room from membership_fee.begins_on
                 .outerjoin(Room, Room.id == func.coalesce(rhe_end.c.room_id, rhe_begin.c.room_id))
                 .outerjoin(Building, Building.id == Room.building_id)
            )
            # Check if a booking already exists on the user account in the fee timespan
            .where(not_(exists(select(None).select_from(split_user_account
                    .join(Transaction, Transaction.id == split_user_account.c.transaction_id)
                    .join(split_fee_account, split_fee_account.c.transaction_id == Transaction.id)
                )
                .where(and_(split_user_account.c.account_id == User.account_id,
                            Transaction.valid_on.between(literal(membership_fee.begins_on),
                                                         literal(membership_fee.ends_on)),
                            split_fee_account.c.account_id.in_(fee_accounts_ids),
                            split_fee_account.c.amount < 0,
                            split_fee_account.c.id != split_user_account.c.id))
            )))
            # Only those users who had the `membership_fee` property on `booking_begin` or
            # `booking_end`
            .where(or_(fee_prop_beginning.column.is_not(None),
                       fee_prop_end.column.is_not(None)))
            .distinct()
            .cte('membership_fee_users'))


@with_transaction
def post_transactions_for_membership_fee(membership_fee, processor, simulate=False):
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

    description = membership_fee_description.format(fee_name=membership_fee.name).to_json()

    # Select all users who fulfill the requirements for the fee in the fee timespan
    users = users_eligible_for_fee_query(membership_fee)

    affected_users_raw = session.session.execute(select(users.c.id,
                                                        users.c.name,
                                                        users.c.fee_account_id)).fetchall()

    if not simulate:
        numbered_users = (select(users.c.id,
                                 users.c.fee_account_id.label('fee_account_id'),
                                 users.c.account_id,
                                 func.row_number().over().label('index'))
                          .select_from(users)
                          .cte("membership_fee_numbered_users"))

        transactions = (Transaction.__table__.insert()
             .from_select([Transaction.description,
                           Transaction.author_id,
                           Transaction.posted_at,
                           Transaction.valid_on,
                           Transaction.confirmed],
                          select(literal(description),
                                 literal(processor.id),
                                 func.current_timestamp(),
                                 literal(membership_fee.ends_on),
                                 True).select_from(users))
             .returning(Transaction.id)
             .cte('membership_fee_transactions'))

        numbered_transactions = (select(transactions.c.id, func.row_number().over().label('index'))
             .select_from(transactions)
             .cte('membership_fee_numbered_transactions'))

        split_insert_fee_account = (Split.__table__.insert()
            .from_select([Split.amount, Split.account_id, Split.transaction_id],
                         select(literal(-membership_fee.regular_fee, type_=Money),
                                numbered_users.c.fee_account_id,
                                numbered_transactions.c.id)
                         .select_from(numbered_users.join(numbered_transactions,
                                                          numbered_transactions.c.index == numbered_users.c.index))
                         )
            .returning(Split.id)
            .cte('membership_fee_split_fee_account'))

        split_insert_user = (Split.__table__.insert().from_select(
            [Split.amount, Split.account_id, Split.transaction_id],
            select(literal(membership_fee.regular_fee, type_=Money),
                   numbered_users.c.account_id,
                   numbered_transactions.c.id)
            .select_from(numbered_users.join(numbered_transactions,
                                             numbered_transactions.c.index == numbered_users.c.index)))
            .returning(Split.id)
            .cte('membership_fee_split_user'))

        session.session.execute(select().select_from(split_insert_fee_account
                                                       .join(split_insert_user,
                                                             split_insert_user.c.id ==
                                                             split_insert_fee_account.c.id)))

    affected_users = [dict(user._mapping) for user in affected_users_raw]

    return affected_users


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


class MT940Record(NamedTuple):
    our_account_number: str
    posted_on: str
    valid_on: str
    type: str
    reference: str
    other_name: str
    other_account_number: str
    other_routing_number: str
    amount: str
    currency: str
    info: str


MT940_FIELDNAMES = MT940Record._fields


class MT940Dialect(csv.Dialect):
    delimiter = ";"
    quotechar = '"'
    doublequote = True
    skipinitialspace = True
    lineterminator = '\n'
    quoting = csv.QUOTE_ALL


class CSVImportError(PycroftLibException):
    def __init__(self, message, cause=None):
        if cause is not None:
            message = gettext("{0}\nCaused by:\n{1}").format(
                message, cause
            )
        self.cause = cause
        super().__init__(message)


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
        raise CSVImportError(gettext("No data present."))
    except csv.Error as e:
        raise CSVImportError(gettext("Could not read CSV."), e)
    if not activities:
        raise CSVImportError(gettext("No data present."))
    if not is_ordered((a[8] for a in activities), operator.ge):
        raise CSVImportError(gettext(
            "Transaction are not sorted according to transaction date in "
            "descending order."))
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
                gettext("Import conflict:\n"
                        "Database bank account activities:\n{0}\n"
                        "File bank account activities:\n{1}").format(
                    '\n'.join(str(x) for x in islice(activities, i1, i2)),
                    '\n'.join(str(x) for x in islice(activities, j1, j2))))
        else:
            raise AssertionError()
    if balance != expected_balance:
        message = gettext("Balance after does not equal expected balance: "
                          "{0} != {1}.")
        raise CSVImportError(message.format(balance, expected_balance))


def remove_space_characters(field):
    """Remove every 28th character if it is a space character."""
    if field is None:
        return None
    return "".join(c for i, c in enumerate(field) if i % 28 != 27 or c != ' ')


# Banks are using the original reference field to store several subfields with
# SEPA. Subfields start with a four letter tag name and the plus sign, they
# are separated by space characters.
sepa_description_field_tags = (
    'EREF', 'KREF', 'MREF', 'CRED', 'DEBT', 'SVWZ', 'ABWA', 'ABWE'
)
sepa_description_pattern = re.compile(''.join(chain(
    '^',
    [fr'(?:({tag}\+.*?)(?: (?!$)|$))?'
     for tag in sepa_description_field_tags],
    '$'
)), re.UNICODE)


def cleanup_description(description):
    match = sepa_description_pattern.match(description)
    if match is None:
        return description
    return ' '.join(remove_space_characters(f) for f in match.groups() if f is not None)


def restore_record(record):
    string_buffer = StringIO()
    csv.DictWriter(
        string_buffer, MT940_FIELDNAMES, dialect=MT940Dialect
    ).writerow(record._asdict())
    restored_record = string_buffer.getvalue()
    string_buffer.close()
    return restored_record


def process_record(index, record, imported_at):
    if record.currency != "EUR":
        message = gettext("Unsupported currency {0}. Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(message.format(record.currency, index, raw_record))
    try:
        bank_account = BankAccount.q.filter_by(
            account_number=record.our_account_number
        ).one()
    except NoResultFound as e:
        message = gettext("No bank account with account number {0}. "
                          "Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.our_account_number, index, raw_record), e)

    try:
        valid_on = datetime.strptime(record.valid_on, "%d.%m.%y").date()
        posted_on = datetime.strptime(record.posted_on, "%d.%m.%y").date()
    except ValueError as e:
        message = gettext("Illegal date format. Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(message.format(index, raw_record), e)

    try:
        amount = Decimal(record.amount.replace(",", "."))
    except ValueError as e:
        message = gettext("Illegal value format {0}. Record {1}: {2}")
        raw_record = restore_record(record)
        raise CSVImportError(
            message.format(record.amount, index, raw_record), e)

    return (amount, bank_account.id, cleanup_description(record.reference),
            record.reference, record.other_account_number,
            record.other_routing_number, record.other_name, imported_at,
            posted_on, valid_on)


def user_has_paid(user):
    return user.account.balance <= 0


def get_typed_splits(
    splits: typing.Sequence[Split],
) -> typing.Iterable[tuple[Split, Split]]:
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
def end_payment_in_default_memberships(processor):
    # TODO remove `type: ignore` once on SQLA2.0 (#562)
    users = (
        User.q.join(User.current_properties)
        .filter(CurrentProperty.property_name == "payment_in_default")
        .join(Account)
        .filter(Account.balance <= 0)  # type: ignore
        .all()
    )

    for user in users:
        if user.member_of(config.payment_in_default_group):
            remove_member_of(user, config.payment_in_default_group, processor,
                             closedopen(session.utcnow() - timedelta(seconds=1), None))

    return users


def get_negative_members():
    # TODO remove `type: ignore` once on SQLA2.0 (#562)
    users = (
        User.q.join(User.current_properties)
        .filter(CurrentProperty.property_name == "membership_fee")
        .join(Account)
        .filter(Account.balance > 0)  # type: ignore
        .all()
    )

    return users


def get_last_payment_in_default_membership(
    session: Session, user: User
) -> Membership | None:
    membership: Membership | None = session.scalars(
        select(Membership)
        .filter(Membership.user_id == user.id)
        .filter(Membership.group_id == config.payment_in_default_group.id)
        .order_by(Membership.active_during.desc())
        .limit(1)
    ).first()
    return membership


def get_users_with_payment_in_default(session: Session) -> tuple[set[User], set[User]]:
    """Determine which users should be blocked and whose membership should be terminated.

    :returns: which users should be added to the ``payment_in_default`` group (``[0]``)
        and which ones should get their membership terminated (``[1]``).
    """
    # Add memberships and end "member" membership if threshold met
    users = get_negative_members()

    users_pid_membership: set[User] = set()
    users_membership_terminated: set[User] = set()

    ts_now = utcnow()
    for user in users:
        in_default_days = user.account.in_default_days

        try:
            fee_date = ts_now - timedelta(days=in_default_days)

            fee = get_membership_fee_for_date(fee_date)
        except NoResultFound:
            fee = get_last_applied_membership_fee()

        if fee is None:
            raise ValueError("No fee found")

        if in_default_days >= fee.payment_deadline.days:
            # Skip user if the payment in default group membership was terminated within the last week
            last_pid_membership = get_last_payment_in_default_membership(session, user)

            if last_pid_membership is not None:
                end = last_pid_membership.active_during.end
                if end is not None and end >= ts_now - timedelta(days=7):
                    continue

            if not user.has_property('payment_in_default'):
                # Add user to new payment in default list
                users_pid_membership.add(user)

        if in_default_days >= fee.payment_deadline_final.days:
            # Add user to terminated memberships
            users_membership_terminated.add(user)

    users_membership_terminated.difference_update(users_pid_membership)

    _bal = operator.attrgetter('account.balance')
    users_pid_membership = set(sorted(users_pid_membership, key=_bal))
    users_membership_terminated = set(sorted(users_membership_terminated, key=_bal))

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
            in_default_days = user.account.in_default_days

            try:
                fee_date = ts_now - timedelta(days=in_default_days)

                fee = get_membership_fee_for_date(fee_date)
            except NoResultFound:
                fee = get_last_applied_membership_fee()

            end_membership_date = utcnow() - (timedelta(days=in_default_days) - fee.payment_deadline_final)

            move_out(user, "Zahlungsrückstand", processor, end_membership_date, True)

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
        query = query.filter(Transaction.description.ilike(f'%{search}%'))

    if positive is not None:
        if positive:
            query = query.filter(Split.amount >= 0)
        else:
            query = query.filter(Split.amount < 0)

    query = query.order_by(text(ordering)).offset(offset).limit(limit)

    if eagerload:
        query = query.options(contains_eager(Split.transaction))

    return query


def match_activities() -> tuple[dict[BankAccountActivity, User], dict[BankAccountActivity, Account]]:
    """For all unmatched transactions, determine which user or team they should be matched with.
    """
    matching: dict[BankAccountActivity, User] = {}
    team_matching: dict[BankAccountActivity, Account] = {}
    stmt = (select(BankAccountActivity)
           .options(joinedload(BankAccountActivity.bank_account))
           .filter(BankAccountActivity.transaction_id.is_(None)))

    def _fetch_normal(uid: int) -> User | None:
        return User.get(uid)

    for activity in session.session.scalars(stmt).all():
        user = match_reference(activity.reference, fetch_normal=_fetch_normal)

        if user:
            matching.update({activity: user})
            continue

        if team := match_team_transaction(activity):
            team_matching.update({activity: team})

    return matching, team_matching


T = TypeVar('T')
U = TypeVar('U')
TUser = TypeVar('TUser')


def _and_then(thing: T | None, f: Callable[[T], U | None]) -> U | None:
    return None if thing is None else f(thing)


def match_reference(reference: str, fetch_normal: Callable[[int], TUser | None]) -> TUser | None:
    """Try to return a user fitting a given bank reference string.

    :param reference: the bank reference
    :param fetch_normal: If we found a pycroft user id, use this to fetch the user.

    Passing lambdas allows us to write fast, db-independent tests.
    """
    # preprocessing
    reference = reference\
        .replace('AWV-MELDEPFLICHT BEACHTENHOTLINE BUNDESBANK.(0800) 1234-111', '')\
        .strip()

    pyc_user = _and_then(match_pycroft_reference(reference), fetch_normal)
    if pyc_user:
        return pyc_user

    return None


def match_pycroft_reference(reference: str) -> int | None:
    """Given a bank reference, return the user id"""
    from pycroft.lib.user import check_user_id

    search = re.findall(r"([\d]{4,6} ?[-/?:,+.]? ?[\d]{1,2})", reference.replace(' ', ''))
    if not search:
        return None

    for group in search:
        try:
            uid = group.replace(' ', '').replace('/', '-') \
                .replace('?', '-').replace(':', '-').replace(',', '-') \
                .replace('+', '-').replace('.', '-')
            if uid[-2] != '-' and uid[-3] != '-':
                # interpret as type 2 UID with missing -
                uid = uid[:-2] + '-' + uid[-2:]

            if check_user_id(uid):
                uid = uid.split("-")[0]
                try:
                    return int(uid)
                except ValueError:
                    continue
        except AttributeError:
            continue

    return None


def match_team_transaction(activity: BankAccountActivity) -> Account | None:
    """Return the first team account that matches a given activity, or None.

    There is no tie-breaking mechanism if multiple patterns match.
    """
    if not activity.matching_patterns:
        return None

    first, *_rest = activity.matching_patterns
    if _rest:
        logger.warning("Ambiguously matched reference: '%s'", activity.reference)

    return first.account


@with_transaction
def transaction_delete(transaction, processor):
    if transaction.confirmed:
        raise ValueError("transaction already confirmed")

    session.session.delete(transaction)

    message = deferred_gettext("Deleted transaction {}.").format(transaction.id)
    log_event(message.to_json(), author=processor)


@with_transaction
def transaction_confirm(transaction, processor):
    if transaction.confirmed:
        raise ValueError("transaction already confirmed")

    transaction.confirmed = True

    message = deferred_gettext("Confirmed transaction {}.").format(transaction.id)
    log_event(message.to_json(), author=processor)


@with_transaction
def transaction_confirm_all(processor):
    # Confirm all transactions older than one hour that are not confirmed yet
    transactions = Transaction.q.filter_by(confirmed=False)\
        .filter(Transaction.posted_at < session.utcnow() - timedelta(hours=1))

    for transaction in transactions:
        transaction_confirm(transaction, processor)


def fee_from_valid_date(session: Session, valid_on: date, account: Account) -> Split | None:
    """If existent, get the membership fee split for a given date"""
    fee: Split | None = session.scalars(
        select(Split)
        .filter_by(account=account)
        .join(Transaction)
        .filter(Split.amount > 0)
        .filter(Transaction.valid_on == valid_on)
        .limit(1)
    ).first()
    return fee


def estimate_balance(session: Session, user, end_date):
    """Estimate the balance a user account will have at :paramref:`end_date`.

    :param session:
    :param user: The member
    :param end_date: Date of the end of the membership
    :return: Estimated balance at the end_date
    """

    now = utcnow().date()

    # Use tomorrow in case that it is the last of the month, the fee for the
    # current month will be added later
    tomorrow = now + timedelta(1)

    last_fee = session.scalars(
        select(MembershipFee).order_by(MembershipFee.ends_on.desc()).limit(1)
    ).first()

    if last_fee is None:
        raise ValueError("no fee information available")

    # Bring end_date to previous month if the end_date is in grace period
    end_date_justified = end_date - timedelta(last_fee.booking_begin.days - 1)

    months_to_pay = diff_month(end_date_justified, tomorrow)

    # If the user has to pay a fee for the current month
    has_to_pay_this_month = user.has_property(
        'membership_fee',
        tomorrow.replace(day=last_fee.booking_end.days)
    )
    if has_to_pay_this_month:
        months_to_pay += 1

    # If there was no fee booked yet for the last month and the user has to pay
    # a fee for the last month, increment months_to_pay
    last_month_last = tomorrow.replace(day=1) - timedelta(1)
    last_month_fee_outstanding = (
        fee_from_valid_date(session, last_month_last, user.account) is None
    )

    if last_month_fee_outstanding:
        had_to_pay_last_month = user.has_property(
            'membership_fee',
            last_month_last.replace(day=last_fee.booking_end.days)
        )
        if had_to_pay_last_month:
            months_to_pay += 1

    # If there is already a fee booked for this month, decrement months_to_pay
    this_month_fee_outstanding = (
        fee_from_valid_date(session, last_day_of_month(tomorrow), user.account) is None
    )
    if not this_month_fee_outstanding:
        months_to_pay -= 1

    return (-user.account.balance) - (months_to_pay * last_fee.regular_fee)


def get_pid_csv():
    from pycroft.lib.user import encode_type2_user_id

    users = get_negative_members()

    f = StringIO()

    writer = csv.writer(f)
    writer.writerow(('id', 'email', 'name', 'balance'))
    writer.writerows((encode_type2_user_id(u.id),
                      f"{u.login}@agdsn.me",
                      u.name,
                      str(-u.account.balance)) for u in users)

    return f.getvalue()


def get_last_import_date(session: Session) -> datetime | None:
    date: datetime | None = session.scalars(
        select(func.max(BankAccountActivity.imported_at))
    ).first()
    return date
