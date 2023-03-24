#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import csv
import operator
import typing as t
from datetime import timedelta
from io import StringIO

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from pycroft import config
from pycroft.helpers.interval import closed, starting_from
from pycroft.lib.logging import log_user_event
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.model import session
from pycroft.model.finance import (
    Account,
    MembershipFee,
)
from pycroft.model.property import CurrentProperty
from pycroft.model.session import with_transaction, utcnow
from pycroft.model.user import User, Membership
from .membership_fee import (
    get_last_applied_membership_fee,
    get_membership_fee_for_date,
)


@with_transaction
def end_payment_in_default_memberships(processor: User) -> t.Sequence[User]:
    users = session.session.scalars(
        select(User)
        .join(User.current_properties)
        .filter(CurrentProperty.property_name == "payment_in_default")
        .join(Account)
        .filter(Account.balance <= 0)
    ).all()

    for user in users:
        if user.member_of(config.payment_in_default_group):
            remove_member_of(
                user,
                config.payment_in_default_group,
                processor,
                starting_from(session.utcnow() - timedelta(seconds=1)),
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


def get_negative_members() -> t.Sequence[User]:
    users = session.session.scalars(
        select(User)
        .join(User.current_properties)
        .filter(CurrentProperty.property_name == "membership_fee")
        .join(Account)
        .filter(Account.balance > 0)
    ).all()

    return users


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

        fee: MembershipFee | None
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

            if not user.has_property("payment_in_default"):
                # Add user to new payment in default list
                users_pid_membership.add(user)

        if in_default_days >= fee.payment_deadline_final.days:
            # Add user to terminated memberships
            users_membership_terminated.add(user)

    users_membership_terminated.difference_update(users_pid_membership)

    _bal = operator.attrgetter("account.balance")
    users_pid_membership = set(sorted(users_pid_membership, key=_bal))
    users_membership_terminated = set(sorted(users_membership_terminated, key=_bal))

    return users_pid_membership, users_membership_terminated


@with_transaction
def take_actions_for_payment_in_default_users(
    users_pid_membership: t.Iterable[User],
    users_membership_terminated: t.Iterable[User],
    processor: User,
) -> None:
    ts_now = session.utcnow()

    for user in users_pid_membership:
        if not user.member_of(config.payment_in_default_group):
            make_member_of(
                user, config.payment_in_default_group, processor, closed(ts_now, None)
            )

    from pycroft.lib.user import move_out

    for user in users_membership_terminated:
        if user.member_of(config.member_group):
            in_default_days = user.account.in_default_days

            fee: MembershipFee | None
            try:
                fee_date = ts_now - timedelta(days=in_default_days)
                fee = get_membership_fee_for_date(fee_date)
            except NoResultFound:
                fee = get_last_applied_membership_fee()
            if fee is None:
                raise ValueError("No fee found")


            end_membership_date = utcnow() - (
                timedelta(days=in_default_days) - fee.payment_deadline_final
            )

            move_out(user, "Zahlungsrückstand", processor, end_membership_date, True)

            log_user_event(
                "Mitgliedschaftsende wegen Zahlungsrückstand.", processor, user
            )


def get_pid_csv() -> str:
    """Generate a CSV file containing all members with negative balance
    (“payment in default”)."""
    from pycroft.lib.user import encode_type2_user_id

    users = get_negative_members()

    f = StringIO()

    writer = csv.writer(f)
    writer.writerow(("id", "email", "name", "balance"))
    writer.writerows(
        (
            encode_type2_user_id(u.id),
            f"{u.login}@agdsn.me",
            u.name,
            str(-u.account.balance),
        )
        for u in users
    )

    return f.getvalue()
