# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from pycroft.model import session
from pycroft.model.dormitory import Room
from pycroft.model.logging import UserLogEntry, RoomLogEntry
from pycroft.model.session import with_transaction
from pycroft.model.user import User


@with_transaction
def _create_log_entry(class_, message, author, created_at=None, **kwargs):
    """
    This method will create a new LogEntry of the given type with the given
    arguments.

    :param type type: A subclass of LogEntry which should be created.
    :param unicode message: the log message text
    :param User author: user responsible for the entry
    :param datetime|None created_at: Creation time of the entry. Defaults to
    current database time if None.
    :param kwargs: Additional arguments.
    :return: the newly created LogEntry.
    """
    if created_at is not None:
        kwargs['created_at'] = created_at
    kwargs['message'] = message
    kwargs['author'] = author
    entry = class_(**kwargs)
    session.session.add(entry)
    return entry


def log_user_event(message, author, user, created_at=None):
    """
    This method will create a new UserLogEntry.

    :param unicode message: the log message text
    :param User author: user responsible for the entry
    :param User user: the user for which the log should be created
    :param datetime|None created_at: Creation time of the entry. Defaults to
    current database time if None.
    :return: the newly created UserLogEntry.
    """
    return _create_log_entry(UserLogEntry, message, author, created_at,
                             user=user)


def log_room_event(message, author, room, created_at=None):
    """
    This method will create a new RoomLogEntry.

    :param unicode message: the log message text
    :param User author: user responsible for the entry
    :param Room room: the room for which the log should be created
    :param datetime|None created_at: Creation time of the entry. Defaults to
    current database time if None.
    :return: the newly created RoomLogEntry.
    """
    return _create_log_entry(RoomLogEntry, message, author, created_at,
                             room=room)
