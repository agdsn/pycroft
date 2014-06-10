from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.property import TrafficGroup, PropertyGroup, Property,\
    Membership, Group


def _create_group(group_type, *args, **kwargs):
    """
    This method will create a new Group.

    :param group_type: the type of the group. Equals the discriminator.
    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created group.
    """
    group_type = str(group_type).lower()

    if group_type == "property_group":
        group = PropertyGroup(*args, **kwargs)
    elif group_type == "traffic_group":
        group = TrafficGroup(*args, **kwargs)
    else:
        raise ValueError("Unknown group type!")

    session.session.add(group)
    return group


@with_transaction
def _delete_group(group_id):
    """
    This method will remove the Group for the given id.

    :param group_id: the id of the Group which should be removed.
    :return: the removed Group.
    """
    group = Group.q.get(group_id)
    if group is None:
        raise ValueError("The given id is wrong!")

    if group.discriminator == "property_group":
        del_group = PropertyGroup.q.get(group_id)
    elif group.discriminator == "traffic_group":
        del_group = TrafficGroup.q.get(group_id)
    else:
        raise ValueError("Unknown group type")

    session.session.delete(del_group)
    return del_group


@with_transaction
def create_traffic_group(name, traffic_limit):
    """
    This method will create a new traffic group.

    :param name: the name of the group
    :param traffic_limit: the traffic limit of the group
    :return: the newly created traffic group
    """
    return _create_group("traffic_group", name=name, traffic_limit=traffic_limit)


@with_transaction
def delete_traffic_group(traffic_group_id):
    """
    This method will remove the traffic group for the given id.

    :param traffic_group_id: the if of the group which should be deleted
    :return: the deleted traffic group
    """
    return _delete_group(traffic_group_id)


@with_transaction
def create_property_group(name):
    """
    This method will create a new property group.

    :param name: the name of the group
    :return: the newly created property group
    """
    return _create_group("property_group", name=name)


@with_transaction
def delete_property_group(property_group_id):
    """
    This method will remove the property group for the given id.

    :param property_group_id: the id of the group which should be removed.
    :return: the deleted property group
    """
    return _delete_group(property_group_id)


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
def create_membership(start_date, end_date, user, group):
    """
    This method will create a new Membership.

    :param start_date: the start date of the membership
    :param end_date: the end date of the membership
    :param user: the user
    :param group: the group
    :return: the newly created Membership
    """
    membership = Membership(start_date=start_date, end_date=end_date,
                            user=user, group=group)
    session.session.add(membership)
    return membership


@with_transaction
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
    return del_membership
