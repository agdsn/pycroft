# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model.logging import UserLogEntry, LogEntry
from pycroft.model import session

def _create_log_entry(type, *args, **kwargs):
    """
    This method will create a new LogEntry of the given type with the given
    arguments.

    :param type: the type of the LogEntry which should be created.
    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created LogEntry.
    """
    type = str(type).lower()

    if type == "userlogentry":
        entry = UserLogEntry(*args, **kwargs)
    else:
        raise ValueError("Unknown LogEntry type!")

    session.session.add(entry)
    session.session.commit()

    return entry

def delete_log_entry(log_entry_id):
    """
    This method will remove the LogEntry for the given id.

    :param log_entry_id: the id of the LogEntry which should be removed.
    :return: the removed LogEntry.
    """
    entry= LogEntry.q.get(log_entry_id)
    if entry is None:
        raise ValueError("The given id is wrong!")

    if entry.discriminator == "userlogentry":
        del_entry = UserLogEntry.q.get(log_entry_id)
    else:
        raise ValueError("Unknown LogEntry type!")

    session.session.delete(del_entry)
    session.session.commit()

    return del_entry


def create_user_log_entry(*args, **kwargs):
    """
    This method will create a new UserLogEntry.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created UserLogEntry.
    """
    return _create_log_entry("userlogentry", *args, **kwargs)
