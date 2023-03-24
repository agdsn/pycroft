#  Copyright (c) 2023. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import logging
import re
from typing import Callable, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from pycroft.model import session
from pycroft.model.finance import BankAccountActivity, Account
from pycroft.model.user import User


logger = logging.getLogger(__name__)

T = TypeVar("T")

def match_activities() -> (
    tuple[dict[BankAccountActivity, User], dict[BankAccountActivity, Account]]
):
    """For all unmatched transactions, determine which user or team they should be matched with."""
    matching: dict[BankAccountActivity, User] = {}
    team_matching: dict[BankAccountActivity, Account] = {}
    stmt = (
        select(BankAccountActivity)
        .options(joinedload(BankAccountActivity.bank_account))
        .filter(BankAccountActivity.transaction_id.is_(None))
    )

    def _fetch_normal(uid: int) -> User | None:
        return session.session.get(User, uid)

    for activity in session.session.scalars(stmt).all():
        user = _match_reference(activity.reference, fetch_normal=_fetch_normal)

        if user:
            matching.update({activity: user})
            continue

        if team := _match_team_transaction(activity):
            team_matching.update({activity: team})

    return matching, team_matching


U = TypeVar("U")


def _and_then(thing: T | None, f: Callable[[T], U | None]) -> U | None:
    return None if thing is None else f(thing)


TUser = TypeVar("TUser")


def _match_reference(
    reference: str, fetch_normal: Callable[[int], TUser | None]
) -> TUser | None:
    """Try to return a user fitting a given bank reference string.

    :param reference: the bank reference
    :param fetch_normal: If we found a pycroft user id, use this to fetch the user.

    Passing lambdas allows us to write fast, db-independent tests.
    """
    # preprocessing
    reference = reference.replace(
        "AWV-MELDEPFLICHT BEACHTENHOTLINE BUNDESBANK.(0800) 1234-111", ""
    ).strip()

    pyc_user = _and_then(_match_pycroft_reference(reference), fetch_normal)
    if pyc_user:
        return pyc_user

    return None


def _match_pycroft_reference(reference: str) -> int | None:
    """Given a bank reference, return the user id"""
    from pycroft.lib.user import check_user_id

    search = re.findall(
        r"([\d]{4,6} ?[-/?:,+.]? ?[\d]{1,2})", reference.replace(" ", "")
    )
    if not search:
        return None

    for group in search:
        try:
            uid = (
                group.replace(" ", "")
                .replace("/", "-")
                .replace("?", "-")
                .replace(":", "-")
                .replace(",", "-")
                .replace("+", "-")
                .replace(".", "-")
            )
            if uid[-2] != "-" and uid[-3] != "-":
                # interpret as type 2 UID with missing -
                uid = uid[:-2] + "-" + uid[-2:]

            if check_user_id(uid):
                uid = uid.split("-")[0]
                try:
                    return int(uid)
                except ValueError:
                    continue
        except AttributeError:
            continue

    return None


def _match_team_transaction(activity: BankAccountActivity) -> Account | None:
    """Return the first team account that matches a given activity, or None.

    There is no tie-breaking mechanism if multiple patterns match.
    """
    if not activity.matching_patterns:
        return None

    first, *_rest = activity.matching_patterns
    if _rest:
        logger.warning("Ambiguously matched reference: '%s'", activity.reference)

    return first.account
