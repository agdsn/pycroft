# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.membership
~~~~~~~~~~~~~~~~~~~~~~

This module contains functions concerning groups, membership, and property
management.

"""
from sqlalchemy import or_, and_, func, distinct
from sqlalchemy.future import select
from sqlalchemy.orm import aliased

from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import UnboundedInterval, IntervalSet, closed
from pycroft.lib.logging import log_user_event, log_event
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import Membership, Property, PropertyGroup


def known_properties() -> set[str]:
    """Return a set of all known properties, granted or denied."""
    return set(session.session.execute(
        select(Property.name).distinct()
    ).scalars())


@with_transaction
def grant_property(group, name):
    """
    Grants a property to a group.

    :param PropertyGroup group: a group
    :param str name: the name of the property
    :return: created or changed property object
    :rtype: Property
    """
    group.property_grants[name] = True
    return group.properties[name]


@with_transaction
def deny_property(group, name):
    """
    Denies a property to a group.

    :param PropertyGroup group: a group
    :param str name: the name of the property
    :return: created or changed property object
    :rtype: Property
    """
    group.property_grants[name] = False
    return group.properties[name]


@with_transaction
def remove_property(group, name):
    """
    Removes a property association (grant or denial) with a given group.

    :param PropertyGroup group: a group
    :param str name: the name of the property
    :raises ValueError: if group doesn't have a property with the given name
    """
    if not group.properties.pop(name, None):
        raise ValueError("Group {0} doesn't have property {1}"
                         .format(group.name, name))


@with_transaction
def make_member_of(user, group, processor, during=UnboundedInterval):
    """
    Makes a user member of a group in a given interval. If the given interval
    overlaps with an existing membership, this method will join the overlapping
    intervals together, so that there will be at most one membership for
    particular user in particular group at any given point in time.

    :param User user: the user
    :param Group group: the group
    :param User processor: User issuing the addition
    :param Interval during:
    """

    if group.permission_level > processor.permission_level:
        raise PermissionError("cannot create a membership for a group with a"
                              " higher permission level")

    memberships: list[Membership] = [
        m for m in user.active_memberships(when=during)
        if m.group == group
    ]
    intervals = IntervalSet(m.active_during.closure for m in memberships).union(during)
    for m in memberships:
        session.session.delete(m)
    session.session.add_all(Membership(active_during=i, user=user, group=group) for i in intervals)
    message = deferred_gettext(u"Added to group {group} during {during}.")
    log_user_event(message=message.format(group=group.name,
                                          during=during).to_json(),
                   user=user, author=processor)


@with_transaction
def remove_member_of(user, group, processor, during=UnboundedInterval):
    """Remove a user from a group in a given interval.

    The interval defaults to the unbounded interval, so that the user
    will be removed from the group at any point in time, **removing
    all memberships** in this group retroactively.

    However, a common use case is terminating a membership by setting
    ``during=closedopen(now, None)``.

    :param User user: the user
    :param Group group: the group
    :param User processor: User issuing the removal
    :param Interval during:
    """

    if group.permission_level > processor.permission_level:
        raise PermissionError("cannot delete a membership for a group with a"
                              " higher permission level")

    memberships: list[Membership] = [
        m for m in user.active_memberships(when=during)
        if m.group == group
    ]
    intervals = IntervalSet(m.active_during.closure for m in memberships).difference(during)
    for m in memberships:
        session.session.delete(m)
    session.session.add_all(Membership(active_during=i, user=user, group=group) for i in intervals)
    message = deferred_gettext(u"Removed from group {group} during {during}.")
    log_user_event(message=message.format(group=group.name,
                                          during=during).to_json(),
                   user=user, author=processor)


@with_transaction
def edit_property_group(group, name, permission_level, processor):
    log_event("Edited property group {} -> {}.".format((group.name, group.permission_level),
                                                      (name, permission_level)),
              processor)

    group.name = name
    group.permission_level = permission_level

@with_transaction
def delete_property_group(group, processor):
    log_event("Deleted property group '{}'.".format(group.name),
              processor)

    session.session.delete(group)


def user_memberships_query(user_id: int, active_groups_only: bool = False):
    memberships = Membership.q.select_from(Membership).filter(Membership.user_id == user_id)
    if active_groups_only:
        memberships = memberships.filter(
            # it is important to use == here, "is" does NOT work
            or_(Membership.begins_at == None,
                Membership.begins_at <= session.utcnow())
        ).filter(
            # it is important to use == here, "is" does NOT work
            or_(Membership.ends_at == None,
                Membership.ends_at > session.utcnow())
        )
    group = aliased(PropertyGroup)
    p_granted = aliased(Property)
    p_denied = aliased(Property)
    memberships = (
        memberships
            .join(group)
            .outerjoin(p_granted, and_(p_granted.property_group_id == group.id,
                                       p_granted.granted == True))
            .add_column(func.array_agg(distinct(p_granted.name))
                        .label('granted'))

            .outerjoin(p_denied, and_(p_denied.property_group_id == group.id,
                                      p_denied.granted == False))
            .add_column(func.array_agg(distinct(p_denied.name))
                        .label('denied'))

            .group_by(Membership.id)
    )
    return memberships
