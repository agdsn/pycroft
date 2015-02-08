# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.property import PropertyGroup, Property, Membership


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
def create_membership(begins_at, ends_at, user, group):
    """
    This method will create a new Membership.

    :param begins_at: the start date of the membership
    :param ends_at: the end date of the membership
    :param user: the user
    :param group: the group
    :return: the newly created Membership
    """
    membership = Membership(begins_at=begins_at, ends_at=ends_at,
                            user=user, group=group)
    session.session.add(membership)
    return membership
