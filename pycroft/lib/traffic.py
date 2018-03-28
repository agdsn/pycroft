# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.traffic
~~~~~~~~~~~~~~~~~~~

This module contains functions concerning traffic group membership, credit
granting, etc.

"""
from operator import attrgetter

from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import closedopen
from pycroft.lib.logging import log_user_event
from pycroft.lib.membership import remove_member_of, make_member_of
from pycroft.model import session
from pycroft.model.logging import UserLogEntry
from pycroft.model.traffic import TrafficCredit
from pycroft.model.user import TrafficGroup
from pycroft.model.session import with_transaction


class NoTrafficGroup(ValueError):
    def __init__(self, message="User has no traffic group"):
        super().__init__(message)


def determine_traffic_group(user, custom_group_id=None):
    """Determine the traffic group for a user by his room or a custom
    choice.

    If the building does not have a ``default_traffic_group``,
    ``None`` is returned.

    :param User user: the user in question
    :param int custom_group_id: the optional id of a custom traffic
        group

    :returns: the traffic group

    :rtype: TrafficGroup | None
    """
    if custom_group_id is not None:
        return TrafficGroup.q.get(custom_group_id)
    return user.room.building.default_traffic_group


def setup_traffic_group(user, processor, custom_group_id=None, terminate_other=False):
    """Add a user to a default or custom traffic group

    If neither a custom group is given, nor the corresponding building
    has a default traffic group, no membership is added.  Group
    removal is executed independent of the latter.

    :param User user: the user
    :param User processor: the processor
    :param int custom_group_id: the id of a custom traffic group.  if
        ``None``, the traffic group of the building is used.
    :param bool terminate_other: Whether to terminate current
        :py:cls:`TrafficGroup` memberships.  Defaults to ``False``
    """
    now = session.utcnow()
    if terminate_other:
        for group in user.traffic_groups:
            remove_member_of(user, group, processor, closedopen(now, None))
    traffic_group = determine_traffic_group(user, custom_group_id)
    if traffic_group is not None:
        make_member_of(user, traffic_group, processor, closedopen(now, None))


def effective_traffic_group(user):
    """Determine the effective traffic_group for a user.

    This picks the group from ``user.traffic_groups`` with the highest
    credit amount.

    :param User user:

    :raises: NoTrafficGroup
    """
    groups = user.traffic_groups
    if not groups:
        raise NoTrafficGroup
    # since python sorts are stable, sorting by two keys can be
    # achieved by first applying the secondary and then the primary
    # order
    secondary_sorted = sorted(groups, key=attrgetter('initial_credit_amount'), reverse=True)
    primary_sorted = sorted(secondary_sorted, key=attrgetter('credit_amount'), reverse=True)
    return primary_sorted[0]


@with_transaction
def grant_initial_credit(user):
    """Grant the maximum initial credit of all the user's groups

    The relevant :py:cls:`TrafficGroup` is the one with the largest
    ``credit_amount``.

    The credit granted amounts to ``initial_credit_amount``.  It is
    currently **independent** of any existing :py:cls:`TrafficCredit`
    or :py:cls:`TrafficVolume` entries, although that feature may be
    added in the future.

    :param User user: the user to grant credit to
    """
    now = session.utcnow()
    group = effective_traffic_group(user)
    credit = TrafficCredit(timestamp=now, amount=group.initial_credit_amount,
                           user_id=user.id)
    session.session.add(credit)


@with_transaction
def grant_regular_credit(user):
    """Grant a user's regular credit

    The relevant :py:cls:`TrafficGroup` is the one with the largest
    ``credit_amount``.

    :param User user: the user to grant credit to
    """
    now = session.utcnow()
    group = effective_traffic_group(user)
    credit = TrafficCredit(timestamp=now, amount=group.credit_amount,
                           user_id=user.id)
    session.session.add(credit)


@with_transaction
def reset_credit(user, processor, target_amount=1*1024**3):
    """Compensate a user's traffic credit to a target amount

    :param User user:
    :param User processor:
    :param int target_amount: The target amount to reach, in bytes.
        Defaults to 1GiB.

    :raises ValueError: if the user's current credit is greater than
        or equal to the given target amount.
    """
    now = session.utcnow()
    difference = target_amount - user.current_credit
    if difference <= 0:
        raise ValueError("The current credit surpasses the target amount."
                         " Only an upwards correction is possible.")

    session.session.add(TrafficCredit(user=user, timestamp=now, amount=difference))
    log_user_event(deferred_gettext("Traffic has ben compensated to 1GiB").to_json(),
                   author=processor,
                   user=user)
