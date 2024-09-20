# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.user
~~~~~~~~~~~~~~~~

This module contains.

:copyright: (c) 2012 by AG DSN.
"""

from pycroft import config
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import Interval, starting_from
from pycroft.helpers.utc import DateTimeTz
from pycroft.lib.logging import log_user_event
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import (
    User,
    PropertyGroup,
)


@with_transaction
def block(
    user: User,
    reason: str,
    processor: User,
    during: Interval[DateTimeTz] | None = None,
    violation: bool = True,
) -> User:
    """Suspend a user during a given interval.

    The user is added to violation_group or blocked_group in a given
    interval.  A reason needs to be provided.

    :param user: The user to be suspended.
    :param reason: The reason for suspending.
    :param processor: The admin who suspended the user.
    :param during: The interval in which the user is
        suspended.  If None the user will be suspendeded from now on
        without an upper bound.
    :param violation: If the user should be added to the violation group

    :return: The suspended user.
    """
    if during is None:
        during = starting_from(session.utcnow())

    if violation:
        make_member_of(user, config.violation_group, processor, during)
    else:
        make_member_of(user, config.blocked_group, processor, during)

    message = deferred_gettext("Suspended during {during}. Reason: {reason}.")
    log_user_event(
        message=message.format(during=during, reason=reason).to_json(), author=processor, user=user
    )
    return user


@with_transaction
def unblock(user: User, processor: User, when: DateTimeTz | None = None) -> User:
    """Unblocks a user.

    This removes his membership of the violation, blocken and payment_in_default
    group.

    Note that for unblocking, no further asynchronous action has to be
    triggered, as opposed to e.g. membership termination.

    :param user: The user to be unblocked.
    :param processor: The admin who unblocked the user.
    :param when: The time of membership termination.  Note
        that in comparison to :py:func:`suspend`, you don't provide an
        _interval_, but a point in time, defaulting to the current
        time.  Will be converted to ``starting_from(when)``.

    :return: The unblocked user.
    """
    if when is None:
        when = session.utcnow()

    during = starting_from(when)
    for group in get_blocked_groups():
        if user.member_of(group, when=during):
            remove_member_of(user=user, group=group, processor=processor, during=during)

    return user


def get_blocked_groups() -> list[PropertyGroup]:
    return [config.violation_group, config.payment_in_default_group, config.blocked_group]
