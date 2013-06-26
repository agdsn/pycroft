# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model.logging import UserLogEntry, LogEntry, RoomLogEntry
from pycroft.model import session


def _create_log_entry(type, commit=True, *args, **kwargs):
    """
    This method will create a new LogEntry of the given type with the given
    arguments.

    :param type: the type of the LogEntry which should be created.
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created LogEntry.
    """
    type = str(type).lower()

    if type == "userlogentry":
        entry = UserLogEntry(*args, **kwargs)
    elif type == "roomlogentry":
        entry = RoomLogEntry(*args, **kwargs)
    else:
        raise ValueError("Unknown LogEntry type!")

    session.session.add(entry)
    if commit:
        session.session.commit()

    return entry


def delete_log_entry(log_entry_id, commit=True):
    """
    This method will remove the LogEntry for the given id.

    :param log_entry_id: the id of the LogEntry which should be removed.
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the removed LogEntry.
    """
    entry = LogEntry.q.get(log_entry_id)
    if entry is None:
        raise ValueError("The given id is wrong!")

    if entry.discriminator == "userlogentry":
        del_entry = UserLogEntry.q.get(log_entry_id)
    elif entry.discriminator == "roomlogentry":
        del_entry = RoomLogEntry.q.get(log_entry_id)
    else:
        raise ValueError("Unknown LogEntry type!")

    session.session.delete(del_entry)
    if commit:
        session.session.commit()

    return del_entry


def create_user_log_entry(message, timestamp, author_id, user_id, commit=True):
    """
    This method will create a new UserLogEntry.

    :param message: the message of the log
    :param timestamp: the timestamp of the log
    :param author_id: the id of the user which created the log
    :param user_id: the id of the user for which the log should be created
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created UserLogEntry.
    """
    return _create_log_entry("userlogentry", message=message,
                             timestamp=timestamp, author_id=author_id,
                             user_id=user_id, commit=commit)


def create_room_log_entry(message, timestamp, author_id, room_id, commit=True):
    """
    This method will create a new RoomLogEntry.

    :param message: the message of the log
    :param timestamp: the timestamp of the log
    :param author_id: the id of the user which created the log
    :param room_id: the id of the room for which the log should be created
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created RoomLogEntry.
    """
    return _create_log_entry("roomlogentry", message=message,
                             timestamp=timestamp, author_id=author_id,
                             room_id=room_id, commit=commit)
