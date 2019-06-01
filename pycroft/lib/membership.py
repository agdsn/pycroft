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
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import UnboundedInterval, IntervalSet, closed
from pycroft.lib.logging import log_user_event, log_event
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import Membership


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
    memberships = session.session.query(Membership).filter(
        Membership.user == user, Membership.group == group,
        Membership.active(during)).all()
    intervals = IntervalSet(
        closed(m.begins_at, m.ends_at) for m in memberships
    ).union(during)
    for m in memberships:
        session.session.delete(m)
    session.session.add_all(
        Membership(begins_at=i.begin, ends_at=i.end, user=user, group=group)
        for i in intervals)
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
    memberships = session.session.query(Membership).filter(
        Membership.user == user, Membership.group == group,
        Membership.active(during)).all()
    intervals = IntervalSet(
        closed(m.begins_at, m.ends_at) for m in memberships
    ).difference(during)
    for m in memberships:
        session.session.delete(m)
    session.session.add_all(
        Membership(begins_at=i.begin, ends_at=i.end, user=user, group=group)
        for i in intervals)
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
