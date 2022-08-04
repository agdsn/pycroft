# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.membership
~~~~~~~~~~~~~~~~~~~~~~

This module contains functions concerning groups, membership, and property
management.

"""
from __future__ import annotations
import typing as t

from sqlalchemy import and_, func, distinct, Result, nulls_last
from sqlalchemy.future import select
from sqlalchemy.orm import aliased, Session
from sqlalchemy.sql import Select, ClauseElement

from pycroft import Config
from pycroft.helpers import utc
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import UnboundedInterval, IntervalSet, Interval, closedopen
from pycroft.helpers.utc import DateTimeTz
from pycroft.lib.logging import log_user_event, log_event
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import Membership, Property, PropertyGroup, User


def known_properties() -> set[str]:
    """Return a set of all known properties, granted or denied."""
    return set(session.session.execute(
        select(Property.name).distinct()
    ).scalars())


@with_transaction
def grant_property(group: PropertyGroup, name: str) -> Property:
    """
    Grants a property to a group.

    :param group: a group
    :param name: the name of the property
    :return: created or changed property object
    """
    group.property_grants[name] = True
    return group.properties[name]


@with_transaction
def deny_property(group: PropertyGroup, name: str) -> Property:
    """
    Denies a property to a group.

    :param group: a group
    :param name: the name of the property
    :return: created or changed property object
    """
    group.property_grants[name] = False
    return group.properties[name]


@with_transaction
def remove_property(group: PropertyGroup, name: str) -> None:
    """
    Removes a property association (grant or denial) with a given group.

    :param group: a group
    :param name: the name of the property
    :raises ValueError: if group doesn't have a property with the given name
    """
    if not group.properties.pop(name, None):
        raise ValueError(f"Group {group.name} doesn't have property {name}")


@with_transaction
def make_member_of(
    user: User,
    group: PropertyGroup,
    processor: User,
    during: Interval[DateTimeTz] = t.cast(  # noqa: B008
        Interval[DateTimeTz], UnboundedInterval
    ),
) -> None:
    """Makes a user member of a group in a given interval.

    If the given interval
    overlaps with an existing membership, this method will join the overlapping
    intervals together, so that there will be at most one membership for
    particular user in particular group at any given point in time.

    :param user: the user
    :param group: the group
    :param processor: User issuing the addition
    :param during:
    """

    if group.permission_level > processor.permission_level:
        raise PermissionError("cannot create a membership for a group with a"
                              " higher permission level")

    memberships: list[Membership] = [
        m for m in user.active_memberships(when=during)
        if m.group == group
    ]
    intervals = IntervalSet[DateTimeTz](
        m.active_during.closure for m in memberships
    ).union(during)
    for m in memberships:
        session.session.delete(m)
    session.session.flush()
    session.session.add_all(Membership(active_during=i, user=user, group=group) for i in intervals)
    message = deferred_gettext("Added to group {group} during {during}.")
    log_user_event(message=message.format(group=group.name,
                                          during=during).to_json(),
                   user=user, author=processor)


@with_transaction
def remove_member_of(
    user: User,
    group: PropertyGroup,
    processor: User,
    during: Interval[DateTimeTz] = t.cast(  # noqa: B008
        Interval[DateTimeTz], UnboundedInterval
    ),
) -> None:
    """Remove a user from a group in a given interval.

    The interval defaults to the unbounded interval, so that the user
    will be removed from the group at any point in time, **removing
    all memberships** in this group retroactively.

    However, a common use case is terminating a membership by setting
    ``during=starting_from(now)``.

    :param user: the user
    :param group: the group
    :param processor: User issuing the removal
    :param during:
    """

    if group.permission_level > processor.permission_level:
        raise PermissionError("cannot delete a membership for a group with a"
                              " higher permission level")

    memberships: list[Membership] = [
        m for m in user.active_memberships(when=during)
        if m.group == group
    ]
    intervals = IntervalSet[DateTimeTz](
        m.active_during.closure for m in memberships
    ).difference(during)
    for m in memberships:
        session.session.delete(m)
    # flush necessary because we otherwise don't have any control
    # over the order of deletion vs. addition
    session.session.flush()
    session.session.add_all(Membership(active_during=i, user=user, group=group) for i in intervals)

    message = deferred_gettext("Removed from group {group} during {during}.")
    log_user_event(message=message.format(group=group.name,
                                          during=during).to_json(),
                   user=user, author=processor)


def delete_membership(
    session: Session,
    membership_id: int,
    processor: User,
) -> None:
    membership = session.get(Membership, membership_id)
    session.delete(membership)
    message = deferred_gettext("Deleted membership of  group {group}.")
    log_user_event(
        message.format(group=membership.group.name).to_json(),
        user=membership.user,
        author=processor,
    )


@with_transaction
def edit_property_group(
    group: PropertyGroup, name: str, permission_level: int, processor: User
) -> None:
    message = deferred_gettext("Edited property group ({}, {}) -> ({}, {}).")\
        .format(group.name, group.permission_level, name, permission_level)
    log_event(message.to_json(), processor)

    group.name = name
    group.permission_level = permission_level

@with_transaction
def delete_property_group(group: PropertyGroup, processor: User) -> None:
    message = deferred_gettext("Deleted property group '{}'.").format(group.name)
    log_event(message.to_json(), processor)
    session.session.delete(group)


def user_memberships_query(
    user_id: int, active_groups_only: bool = False
) -> Result[tuple[Membership, list[str], list[str]]]:
    memberships = select(Membership).filter(Membership.user_id == user_id)
    if active_groups_only:
        memberships = memberships.filter(
            Membership.active_during.contains(func.current_timestamp())
        )
    group = aliased(PropertyGroup)
    p_granted = aliased(Property)
    p_denied = aliased(Property)
    memberships = (
        memberships.join(group, Membership.group_id == group.id)
        .outerjoin(
            p_granted, and_(p_granted.property_group_id == group.id, p_granted.granted)
        )
        .add_columns(func.array_agg(distinct(p_granted.name)).label("granted"))
        .outerjoin(
            p_denied, and_(p_denied.property_group_id == group.id, ~p_denied.granted)
        )
        .add_columns(func.array_agg(distinct(p_denied.name)).label("denied"))
        .group_by(Membership.id)
    )
    return session.session.execute(memberships)


def change_membership_active_during(
    session: Session,
    membership_id: int,
    begins_at: DateTimeTz,
    ends_at: DateTimeTz | None,
    processor: User,
) -> None:
    """modify the active_during field of a membership"""

    membership = session.get(Membership, membership_id)
    membership.active_during = closedopen(utc.with_min_time(begins_at), ends_at)

    message = (
        deferred_gettext("Edited the membership of group '{group}'. During: {during}")
        .format(group=membership.group.name, during=membership.active_during)
        .to_json()
    )
    log_user_event(message, processor, membership.user)


def select_user_and_last_mem() -> Select:  # Select[Tuple[int, int, str]]
    """Select users with their last membership of a user in the ``member`` group.

    :returns: a select statement with columns ``user_id``, ``mem_id``, ``mem_end``.
    """
    mem_ends_at = func.upper(Membership.active_during)
    window_args: dict[str, ClauseElement | t.Sequence[ClauseElement | str] | None] = {
        "partition_by": User.id,
        "order_by": nulls_last(mem_ends_at),
    }
    return (
        select(
            User.id.label("user_id"),
            func.last_value(Membership.id)
            .over(**window_args, rows=(None, None))
            .label("mem_id"),
            func.last_value(mem_ends_at)
            .over(**window_args, rows=(None, None))
            .label("mem_end"),
        )
        .select_from(User)
        .distinct()
        .join(Membership)
        .join(Config, Config.member_group_id == Membership.group_id)
    )
