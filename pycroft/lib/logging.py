# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.logging
~~~~~~~~~~~~~~~~~~~
"""
import typing as t
from datetime import datetime

from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.logging import UserLogEntry, RoomLogEntry, LogEntry, \
    TaskLogEntry
from pycroft.model.task import Task
from pycroft.model.user import User


def _create_log_entry[
    TLogEntry: LogEntry
](
    class_: type[TLogEntry],
    message: str,
    author: User,
    created_at: datetime | None = None,
    **kwargs: t.Any,
) -> TLogEntry:
    """
    This method will create a new LogEntry of the given type with the given
    arguments.

    :param class_: A subclass of LogEntry which should be created.
    :param message: the log message text
    :param author: user responsible for the entry
    :param created_at: Creation time of the entry. Defaults to current database time if None.
    :param kwargs: Additional arguments to use for instantiation.
    :return: the newly created LogEntry.
    """
    if created_at is not None:
        kwargs['created_at'] = created_at
    kwargs['message'] = message
    kwargs['author'] = author
    entry = class_(**kwargs)
    session.session.add(entry)
    return entry


def log_event(
    message: str, author: User, created_at: datetime | None = None
) -> LogEntry:
    """
    This method will create a new LogEntry.

    :param message: the log message text
    :param author: user responsible for the entry
    :param created_at: Creation time of the entry. Defaults to current database time if None.
    :return: the newly created RoomLogEntry.
    """
    return _create_log_entry(LogEntry, message, author, created_at)


def log_task_event(
    message: str, author: User, task: Task, created_at: datetime | None = None
) -> TaskLogEntry:
    """
    This method will create a new TaskLogEntry.

    :param message: the log message text
    :param author: user responsible for the entry
    :param task: the task for which the log should be created
    :param created_at: Creation time of the entry. Defaults to current database time if None.
    :return: the newly created UserLogEntry.
    """
    return _create_log_entry(TaskLogEntry, message, author, created_at,
                             task=task)


def log_user_event(
    message: str, author: User, user: User, created_at: datetime | None = None
) -> UserLogEntry:
    """
    This method will create a new UserLogEntry.

    :param message: the log message text
    :param author: user responsible for the entry
    :param user: the user for which the log should be created
    :param created_at: Creation time of the entry. Defaults to current database time if None.
    :return: the newly created UserLogEntry.
    """
    return _create_log_entry(UserLogEntry, message, author, created_at,
                             user=user)


def log_room_event(
    message: str, author: User, room: Room, created_at: datetime | None = None
) -> RoomLogEntry:
    """
    This method will create a new RoomLogEntry.

    :param message: the log message text
    :param author: user responsible for the entry
    :param room: the room for which the log should be created
    :param created_at: Creation time of the entry. Defaults to current database time if None.
    :return: the newly created RoomLogEntry.
    """
    return _create_log_entry(RoomLogEntry, message, author, created_at,
                             room=room)
