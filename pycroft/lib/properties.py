# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model import session
from pycroft.model.properties import TrafficGroup, PropertyGroup, Property,\
    Membership, Group


def _create_group(type, *args, **kwargs):
    """
    This method will create a new Group.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created group.
    """
    type = str(type).lower()

    if type == "propertygroup":
        group = PropertyGroup(*args, **kwargs)
    elif type == "trafficgroup":
        group = TrafficGroup(*args, **kwargs)
    else:
        raise ValueError("Unknown group type!")

    session.session.add(group)
    session.session.commit()

    return group


def _delete_group(group_id):
    """
    This method will remove the Group for the given id.

    :param group_id: the id of the Group which should be removed.
    :return: the removed Group.
    """
    group = Group.q.get(group_id)
    if group is None:
        raise ValueError("The given id is wrong!")

    if group.discriminator == "propertygroup":
        del_group = PropertyGroup.q.get(group_id)
    elif group.discriminator == "trafficgroup":
        del_group = TrafficGroup.q.get(group_id)
    else:
        raise ValueError("Unknown group type")

    session.session.delete(del_group)
    session.session.commit()

    return del_group


def create_traffic_group(*args, **kwargs):
    """
    This method will create a new traffic group.

    :param args: the arguments passes to the constructor.
    :param kwargs: the keyword arguments passes to the constructor
    :return: the newly created traffic group
    """
    return _create_group("trafficgroup", *args, **kwargs)


def delete_traffic_group(traffic_group_id):
    """
    This method will remove the traffic group for the given id.

    :param traffic_group_id: the if of the group which should be deleted
    :return: the deleted traffic group
    """
    return _delete_group(traffic_group_id)


def create_property_group(*args, **kwargs):
    """
    This method will create a new property group.

    :param args: the positionals which will be passes to the constructor
    :param kwargs: the keyword arguments which will be passed to the constructor
    :return: the newly created property group
    """
    return _create_group("propertygroup", *args, **kwargs)


def delete_property_group(property_group_id):
    """
    This method will remove the property group for the given id.

    :param property_group_id: the id of the grouo which should be removed.
    :return: the deleted property group
    """
    return _delete_group(property_group_id)


def create_property(group_id, *args, **kwargs):
    """
    This method will create a new property and add it to the property group
    represented by the id.

    :param group_id: the id of the property group where the property
                     should be added
    :param args: the positionals which will be passed to the constructor
    :param kwargs: the keyword arguments which will be passed to the constructor
    :return: the newly created property and the group it was added to
    """
    property_group = PropertyGroup.q.get(group_id)
    if property_group is None:
        raise ValueError("The given id is wrong! No property group exists!")

    if "property_group_id" not in kwargs:
        kwargs["property_group_id"] = property_group.id
    elif kwargs["property_group_id"] != group_id:
        raise ValueError(
            "The group id for the constructor of the property differs" +
            " from the id of the group to which the property should be added!")

    property = Property(*args, **kwargs)
    session.session.add(property)
    session.session.commit()

    return property_group, property


def delete_property(group_id, property_name):
    """
    This method will remove the property for the given name form the given group.
limit
    :param group_id: the id of the property group which contains this property.
    :param property_name: the name of the property which should be removed.
    :return: the group and the property which was deleted
    """
    group = PropertyGroup.q.get(group_id)
    if group is None:
        raise ValueError("The given group id is wrong!")

    property = Property.q.filter(Property.name == property_name).first()
    if property is None:
        raise ValueError("The given property name is wrong!")

    if not group.has_property(property.name):
        raise ValueError(
            "The given property group doesn't have the given property")

    session.session.delete(property)
    session.session.commit()

    return group, property


def create_membership(*args, **kwargs):
    """
    This method will create a new Membership.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created Membership
    """
    membership = Membership(*args, **kwargs)
    session.session.add(membership)
    session.session.commit()

    return membership


def delete_membership(membership_id):
    """
    This method will remove the Membership for the given id.

    :param membership_id: the id of the Membership which should be removed.
    :return: the removed membership.
    """
    del_membership = Membership.q.get(membership_id)
    if del_membership is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_membership)
    session.session.commit()

    return del_membership





