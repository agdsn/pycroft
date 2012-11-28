# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model.dormitory import Dormitory, Room
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
    :return: nothing
    """
    dormitory = Dormitory.q.get(dormitory_id)
    if dormitory is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(dormitory)
    session.session.commit()


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
    :return: nothing
    """
    room = Room.q.get(room_id)
    if room is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(room)
    session.session.commit()

