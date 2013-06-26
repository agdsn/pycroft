from pycroft.model import session
from pycroft.model.property import TrafficGroup, PropertyGroup, Property,\
    Membership, Group


def _create_group(type, commit=True, *args, **kwargs):
    """
    This method will create a new Group.

    :param type: the type of the group. Equals the discriminator.
    :param commit: flag which indicates whether the session should be commited
                   or not. Default: True
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
    if commit:
        session.session.commit()

    return group


def _delete_group(group_id, commit = True):
    """
    This method will remove the Group for the given id.

    :param group_id: the id of the Group which should be removed.
    :param commit: flag which indicates whether the session should be commited
                   or not. Default: True
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
    if commit:
        session.session.commit()

    return del_group


def create_traffic_group(name, traffic_limit, commit=True):
    """
    This method will create a new traffic group.

    :param name: the name of the group
    :param traffic_limit: the traffic limit of the group
    :param commit: flag which indicates whether the session should be commited
                   or not. Default: True
    :return: the newly created traffic group
    """
    return _create_group("trafficgroup", name=name, traffic_limit=traffic_limit,
                         commit=commit)


def delete_traffic_group(traffic_group_id, commit=True):
    """
    This method will remove the traffic group for the given id.

    :param traffic_group_id: the if of the group which should be deleted
    :param commit: flag which indicates whether the session should be commited
                   or not. Default: True
    :return: the deleted traffic group
    """
    return _delete_group(traffic_group_id, commit=commit)


def create_property_group(name, commit=True):
    """
    This method will create a new property group.

    :param name: the name of the group
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created property group
    """
    return _create_group("propertygroup", name=name, commit=commit)


def delete_property_group(property_group_id, commit=True):
    """
    This method will remove the property group for the given id.

    :param property_group_id: the id of the group which should be removed.
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the deleted property group
    """
    return _delete_group(property_group_id, commit=commit)


def create_property(name, property_group_id, granted, commit=True):
    """
    This method will create a new property and add it to the property group
    represented by the id.

    :param name: the name of the property
    :param property_group_id: the property group which should have the property
    :param granted: the granted status of the property
    :param commit: frag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created property and the group it was added to
    """
    property_group = PropertyGroup.q.get(property_group_id)
    if property_group is None:
        raise ValueError("The given id is wrong! No property group exists!")

    property = Property(name=name, property_group_id=property_group_id,
                        granted=granted)
    session.session.add(property)
    if commit:
        session.session.commit()

    return property_group, property


def delete_property(property_group_id, name, commit=True):
    """
    This method will remove the property for the given name form the given group.
    limit
    :param property_group_id: the id of the property group which contains this property.
    :param name: the name of the property which should be removed.
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the group and the property which was deleted
    """
    group = PropertyGroup.q.get(property_group_id)
    if group is None:
        raise ValueError("The given group id is wrong!")

    property = Property.q.filter(Property.name == name).first()
    if property is None:
        raise ValueError("The given property name is wrong!")

    if not group.has_property(property.name):
        raise ValueError(
            "The given property group doesn't have the given property")

    session.session.delete(property)
    if commit:
        session.session.commit()

    return group, property


def create_membership(start_date, end_date, user_id, group_id, commit=True):
    """
    This method will create a new Membership.

    :param start_date: the start date of the membership
    :param end_date: the end date of the membership
    :param user_id: the id of the user
    :param group_id: the id of the group
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created Membership
    """
    membership = Membership(start_date=start_date, end_date=end_date,
                            user_id=user_id, group_id=group_id)
    session.session.add(membership)
    if commit:
        session.session.commit()

    return membership


def delete_membership(membership_id, commit=True):
    """
    This method will remove the Membership for the given id.

    :param membership_id: the id of the Membership which should be removed.
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the removed membership.
    """
    del_membership = Membership.q.get(membership_id)
    if del_membership is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_membership)
    if commit:
        session.session.commit()

    return del_membership
