# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.logging import UserLogEntry, RoomLogEntry


@with_transaction
def _create_log_entry(class_, message, author, timestamp=None, **kwargs):
    """
    This method will create a new LogEntry of the given type with the given
    arguments.

    :param type: the type of the LogEntry which should be created.
    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created LogEntry.
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    kwargs['message'] = message
    kwargs['timestamp'] = timestamp
    kwargs['author'] = author
    entry = class_(**kwargs)
    session.session.add(entry)
    return entry


def log_user_event(message, author, user, timestamp=None):
    """
    This method will create a new UserLogEntry.

    :param message: the message of the log
    :param author: the user which created the log
    :param user: the user for which the log should be created
    :param timestamp: the timestamp of the log. Defaults to current time.
    :return: the newly created UserLogEntry.
    """
    return _create_log_entry(UserLogEntry, message, author, timestamp,
                             user=user)


def log_room_event(message, author, room, timestamp=None):
    """
    This method will create a new RoomLogEntry.

    :param message: the message of the log
    :param author: the user which created the log
    :param room: the room for which the log should be created
    :param timestamp: the timestamp of the log. Defaults to current time.
    :return: the newly created RoomLogEntry.
    """
    return _create_log_entry(RoomLogEntry, message, author, timestamp,
                             room=room)
