#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing
import typing as t
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import (
    select,
    between,
    func,
    CTE,
    union,
    future,
    literal,
    and_,
    not_,
    exists,
    or_,
)
from sqlalchemy.orm import Session

from pycroft import Config, config
from pycroft.helpers.date import diff_month, last_day_of_month
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.utc import with_min_time, with_max_time
from pycroft.model import session
from pycroft.model.facilities import Building, Room
from pycroft.model.finance import MembershipFee, Split, Account, Transaction
from pycroft.model.property import evaluate_properties
from pycroft.model.session import with_transaction, utcnow
from pycroft.model.types import Money
from pycroft.model.user import RoomHistoryEntry, User


def get_membership_fee_for_date(target_date: date) -> MembershipFee:
    """
    Get the membership fee which contains a given target date.

    :param target_date: The date for which a corresponding membership fee should be found.
    :raises sqlalchemy.exc.NoResultFound: if no membership fee was found
    :raises sqlalchemy.exc.MultipleResultsFound: if multiple membership fees
        were found:
    """
    return session.session.scalars(
        select(MembershipFee).filter(
            between(target_date, MembershipFee.begins_on, MembershipFee.ends_on)
        )
    ).one()


def get_last_membership_fee(session: Session) -> MembershipFee | None:
    # TODO evaluate whether makes sense,
    #  or whether we should just use the last applied membership fee
    return session.scalar(select(MembershipFee).order_by(MembershipFee.id.desc()))


def get_last_applied_membership_fee() -> MembershipFee | None:
    """Get the last applied membership fee."""
    return session.session.scalar(
        select(MembershipFee)
        .filter(MembershipFee.ends_on <= func.current_timestamp())
        .order_by(MembershipFee.ends_on.desc())
    )


def get_first_applied_membership_fee() -> MembershipFee | None:
    """Get the first applied membership fee."""
    return session.session.scalar(
        select(MembershipFee).order_by(MembershipFee.ends_on.desc())
    )


membership_fee_description = deferred_gettext("Mitgliedsbeitrag {fee_name}")


@typing.no_type_check
# this „2.0-style select“ is only completely supported on a typing level when we have the v2.0
#  typing infrastructure (post-mypy plugin).
#  See https://docs.sqlalchemy.org/en/14/orm/extensions/mypy.html#mypy-pep-484-support-for-orm-mappings
# See also #562
def users_eligible_for_fee_query(membership_fee: MembershipFee) -> CTE:
    split_user_account = Split.__table__.alias()
    split_fee_account = Split.__table__.alias()

    rhe_end = RoomHistoryEntry.__table__.alias()
    rhe_begin = RoomHistoryEntry.__table__.alias()

    fee_account_ids_stmt = union(
        select(Account.id).join(Building).distinct(Account.id),
        select(Config.membership_fee_account_id),
    )
    fee_accounts_ids = set(session.session.scalars(fee_account_ids_stmt))

    properties_beginning_timestamp = with_min_time(
        membership_fee.begins_on + membership_fee.booking_begin - timedelta(1)
    )
    properties_end_timestamp = with_max_time(
        membership_fee.begins_on + membership_fee.booking_end - timedelta(1)
    )

    begin_tstz = with_min_time(membership_fee.begins_on)
    end_tstz = with_max_time(membership_fee.ends_on)

    fee_prop_beginning = evaluate_properties(
        properties_beginning_timestamp, name="fee_prop_beg"
    )
    fee_prop_end = evaluate_properties(properties_end_timestamp, name="fee_prop_end")

    return (
        future.select(
            User.id.label("id"),
            User.name.label("name"),
            User.account_id.label("account_id"),
            # Select fee_account_id of the building or the default
            # fee_account_id if user was not living in a room at booking time
            func.coalesce(
                Building.fee_account_id, literal(config.membership_fee_account_id)
            ).label("fee_account_id"),
        )
        .select_from(
            User.__table__
            # The first two joins are there for filtering reasons (does this user have to pay?)
            # ----
            # `membership_fee` flag on booking_begin, if existent
            .outerjoin(
                fee_prop_beginning,
                and_(
                    fee_prop_beginning.c.user_id == User.id,
                    fee_prop_beginning.c.property_name == "membership_fee",
                    not_(fee_prop_beginning.c.denied),
                ),
            )
            # `membership_fee` flag on booking_end, if existent
            .outerjoin(
                fee_prop_end,
                and_(
                    fee_prop_end.c.user_id == User.id,
                    fee_prop_end.c.property_name == "membership_fee",
                    not_(fee_prop_end.c.denied),
                ),
            )
            # The following joins are there to get a meaningful `account_id` for the user
            # ----
            # Join RoomHistoryEntry, Room and Building of the user at membership_fee.ends_on
            .outerjoin(
                rhe_end,
                and_(
                    rhe_end.c.user_id == User.id,
                    # Only join RoomHistoryEntry that is relevant
                    # on the fee interval end date
                    literal(end_tstz).op("<@")(rhe_end.c.active_during),
                ),
            )
            # Join RoomHistoryEntry, Room and Building of the user at membership_fee.begins_on
            # As second option if user moved out within the month
            .outerjoin(
                rhe_begin,
                and_(
                    rhe_begin.c.user_id == User.id,
                    # Only join RoomHistoryEntry that is relevant
                    # on the fee interval end date
                    literal(begin_tstz).op("<@")(rhe_begin.c.active_during),
                ),
            )
            # Join with Room from membership_fee.ends_on if available,
            # if not, join with the Room from membership_fee.begins_on
            .outerjoin(
                Room, Room.id == func.coalesce(rhe_end.c.room_id, rhe_begin.c.room_id)
            ).outerjoin(Building, Building.id == Room.building_id)
        )
        # Check if a booking already exists on the user account in the fee timespan
        .where(
            not_(
                exists(
                    select(None)
                    .select_from(
                        split_user_account.join(
                            Transaction,
                            Transaction.id == split_user_account.c.transaction_id,
                        ).join(
                            split_fee_account,
                            split_fee_account.c.transaction_id == Transaction.id,
                        )
                    )
                    .where(
                        and_(
                            split_user_account.c.account_id == User.account_id,
                            Transaction.valid_on.between(
                                literal(membership_fee.begins_on),
                                literal(membership_fee.ends_on),
                            ),
                            split_fee_account.c.account_id.in_(fee_accounts_ids),
                            split_fee_account.c.amount < 0,
                            split_fee_account.c.id != split_user_account.c.id,
                        )
                    )
                )
            )
        )
        # Only those users who had the `membership_fee` property on `booking_begin` or
        # `booking_end`
        .where(
            or_(
                fee_prop_beginning.column.is_not(None), fee_prop_end.column.is_not(None)
            )
        )
        .distinct()
        .cte("membership_fee_users")
    )


class AffectedUserInfo(t.TypedDict):
    id: int
    name: str
    fee_account_id: int


@with_transaction
def post_transactions_for_membership_fee(
    membership_fee: MembershipFee, processor: User, simulate: bool = False
) -> list[AffectedUserInfo]:
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
        fee_name=membership_fee.name
    ).to_json()

    # Select all users who fulfill the requirements for the fee in the fee timespan
    users = users_eligible_for_fee_query(membership_fee)

    affected_users_raw = session.session.execute(
        select(users.c.id, users.c.name, users.c.fee_account_id)
    ).fetchall()

    if not simulate:
        numbered_users = (
            select(
                users.c.id,
                users.c.fee_account_id.label("fee_account_id"),
                users.c.account_id,
                func.row_number().over().label("index"),
            )
            .select_from(users)
            .cte("membership_fee_numbered_users")
        )

        # TODO use new-style insert(Transaction)
        transactions = (
            Transaction.__table__.insert()  # type: ignore
            .from_select(
                [
                    Transaction.description,
                    Transaction.author_id,
                    Transaction.posted_at,
                    Transaction.valid_on,
                    Transaction.confirmed,
                ],
                select(
                    literal(description),
                    literal(processor.id),
                    func.current_timestamp(),
                    literal(membership_fee.ends_on),
                    literal(True),
                ).select_from(users),
            )
            .returning(Transaction.id)
            .cte("membership_fee_transactions")
        )

        numbered_transactions = (
            select(
                transactions.c.id,
                func.row_number().over().label("index"),
            )
            .select_from(transactions)
            .cte("membership_fee_numbered_transactions")
        )

        # TODO use new-style insert(Split)
        split_insert_fee_account = (
            Split.__table__.insert()  # type: ignore
            .from_select(
                [Split.amount, Split.account_id, Split.transaction_id],
                select(
                    literal(-membership_fee.regular_fee, type_=Money),
                    numbered_users.c.fee_account_id,
                    numbered_transactions.c.id,
                ).select_from(
                    numbered_users.join(
                        numbered_transactions,
                        numbered_transactions.c.index == numbered_users.c.index,
                    )
                ),
            )
            .returning(Split.id)
            .cte("membership_fee_split_fee_account")
        )

        # TODO use new-style insert(Split)
        split_insert_user = (
            Split.__table__.insert()  # type: ignore
            .from_select(
                [Split.amount, Split.account_id, Split.transaction_id],
                select(
                    literal(membership_fee.regular_fee, type_=Money),
                    numbered_users.c.account_id,
                    numbered_transactions.c.id,
                ).select_from(
                    numbered_users.join(
                        numbered_transactions,
                        numbered_transactions.c.index == numbered_users.c.index,
                    )
                ),
            )
            .returning(Split.id)
            .cte("membership_fee_split_user")
        )

        session.session.execute(
            select().select_from(
                split_insert_fee_account.join(
                    split_insert_user,
                    split_insert_user.c.id == split_insert_fee_account.c.id,
                )
            )
        )

    return [
        t.cast(AffectedUserInfo, dict(user._mapping)) for user in affected_users_raw
    ]


def fee_from_valid_date(
    session: Session, valid_on: date, account: Account
) -> Split | None:
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


def estimate_balance(session: Session, user: User, end_date: date) -> Decimal:
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
        "membership_fee", with_min_time(tomorrow.replace(day=last_fee.booking_end.days))
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
            "membership_fee",
            with_min_time(last_month_last.replace(day=last_fee.booking_end.days)),
        )
        if had_to_pay_last_month:
            months_to_pay += 1

    # If there is already a fee booked for this month, decrement months_to_pay
    this_month_fee_outstanding = (
        fee_from_valid_date(session, last_day_of_month(tomorrow), user.account) is None
    )
    if not this_month_fee_outstanding:
        months_to_pay -= 1

    return t.cast(
        Decimal, (-user.account.balance) - (months_to_pay * last_fee.regular_fee)
    )
