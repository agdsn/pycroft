"""
web.blueprints.helpers.log

This module provides formatter functions that normalize the different
sources of logs to a dict.  The latter represents a valid table row to
:class:`LogTableExtended`.

"""
import typing as t
from datetime import datetime, timezone
from functools import partial

from flask import url_for

from hades_logs import RadiusLogEntry
from pycroft.helpers.i18n import Message
from pycroft.model.logging import LogEntry
from web.table.table import (
    datetime_format,
    UserColResponseNative,
    UserColResponsePlain,
)
from .log_tables import LogType, LogTableRow

from web.template_filters import datetime_filter


def format_log_entry(entry: LogEntry, log_type: LogType) -> LogTableRow:
    return LogTableRow(
        created_at=datetime_format(entry.created_at, formatter=datetime_filter),
        user=UserColResponseNative(
            title=entry.author.name,
            href=url_for("user.user_show", user_id=entry.author.id),
        ),
        message=Message.from_json(entry.message).localize(),
        type=log_type,
    )


format_user_log_entry = partial(format_log_entry, log_type='user')
format_task_log_entry = partial(format_log_entry, log_type='task')
format_room_log_entry = partial(format_log_entry, log_type='room')


class SupportsFormat(t.Protocol):
    def __str__(self) -> str:
        ...

    def __format__(self, format_spec: t.Any) -> str:
        ...


def radius_description(interface: SupportsFormat, entry: RadiusLogEntry) -> str:
    """Build a readable log message from a radius log entry.

    :param interface: Something whose string representation can be
        used to inform about the port the radius log happened.  For
        instance, this can be a :class:`SwitchPort` object
        formatting itself to `switch-wu5-00 (D15)` or similar.
    :param entry: A :class:`RadiusLogEntry` as
        obtained from a :class:`HadesLogs` lookup.
    """
    prefix = f"{interface} – {entry.mac} – "
    if not entry:
        msg = ("REJECTED - This should never happen!"
               " Please contact a root of your choice.")
    else:
        msg = "Groups: {}, VLANs: {}".format(", ".join(entry.groups),
                                             ", ".join(entry.vlans))
    return prefix + msg


def format_hades_log_entry(
    interface: SupportsFormat, entry: RadiusLogEntry
) -> LogTableRow:
    """Turn Radius Log entry information into a canonical form

    This utilizes :py:func:`radius_description` but returns a dict in
    a format conforming with other log sources' output (consider user
    and room logs)

    :param interface: See :py:func:`radius_description`.
    :param entry: See :py:func:`radius_description`.
    """
    date = entry.time
    desc = radius_description(interface, entry)
    return LogTableRow(
        created_at=datetime_format(date, formatter=datetime_filter),
        user=UserColResponsePlain(title="Radius"),
        message=desc,
        type="hades",
    )


def format_custom_hades_message(message: str) -> LogTableRow:
    date = datetime.now(tz=timezone.utc)
    return LogTableRow(
        created_at=datetime_format(date, formatter=datetime_filter),
        user=UserColResponsePlain(title="Radius"),
        message=message,
        type="hades",
    )


_msg_disabled = ("WARNING: The HadesLogs extension is not configured properly. "
                       "Logs cannot be displayed.")
_msg_disconnected = ("None of this user's hosts (if any) are in a connected room. "
                     "Logs cannot be displayed.")
_msg_error = "WARNING: an error occurred when fetching hades logs."
_msg_timeout = "WARNING: Timeout when fetching hades logs."
format_hades_disabled = partial(format_custom_hades_message, message=_msg_disabled)
format_user_not_connected = partial(format_custom_hades_message, message=_msg_disconnected)
format_hades_error = partial(format_custom_hades_message, message=_msg_error)
format_hades_timeout = partial(format_custom_hades_message, message=_msg_timeout)
