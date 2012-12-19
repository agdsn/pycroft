# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model.dormitory import Dormitory, Room, Subnet, VLan
from pycroft.model import session

def create_dormitory(*args, **kwargs):
    """
    This method will create a new dormitory.

    :param args: the arguments which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor
    :return: the newly created dormitory
    """
    dormitory = Dormitory(*args, **kwargs)
    session.session.add(dormitory)
    session.session.commit()

    return dormitory


def delete_dormitory(dormitory_id):
    """
    This method will remove the dormitory fot the given id.

    :param dormitory_id: the id of the dormitory which should be removed
    :return: the deleted dormitory
    """
    dormitory = Dormitory.q.get(dormitory_id)
    if dormitory is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(dormitory)
    session.session.commit()

    return dormitory


def create_room(*args, **kwargs):
    """
    This method creates a new room.

    :param args: arguments which will be passed to the constructor
    :param kwargs: the keyword arguments which will be passed to the constructor
    :return: the newly created room
    """
    room = Room(*args, **kwargs)
    session.session.add(room)
    session.session.commit()

    return room


def delete_room(room_id):
    """
    This method will remove the room for the given id.

    :param room_id: the id of the room which should be deleted
    :return: the deleted room
    """
    room = Room.q.get(room_id)
    if room is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(room)
    session.session.commit()

    return room


def create_subnet(*args, **kwargs):
    """
    This method will create a new subnet.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created subnet.
    """
    subnet = Subnet(*args, **kwargs)
    session.session.add(subnet)
    session.session.commit()

    return subnet


def delete_subnet(subnet_id):
    """
    This method will remove the subnet for the given id.

    :param subnet_id: the id of the subnet which should be removed.
    :return: the removed subnet.
    """
    subnet = Subnet.q.get(subnet_id)
    if subnet is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(subnet)
    session.session.commit()

    return subnet


def create_vlan(*args, **kwargs):
    """
    This method will create a new vlan.

    :param args: the positionals which will be passed to the constructor,
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created vlan.
    """
    vlan = VLan(*args, **kwargs)
    session.session.add(vlan)
    session.session.commit()

    return vlan


def delete_vlan(vlan_id):
    """
    This method will remove the vlan for the given id.

    :param vlan_id: the id of the vlan which should be removed.
    :return: the removed vlan.
    """
    vlan = VLan.q.get(vlan_id)
    if vlan is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(vlan)
    session.session.commit()

    return vlan
