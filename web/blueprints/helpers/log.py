"""
web.blueprints.helpers.log

This module provides formatter functions that normalize the different
sources of logs to a dict.  The latter represents a valid table row to
:py:cls:`LogTableExtended`.

"""
from datetime import datetime, timezone
from functools import partial

from flask import url_for

from pycroft.helpers.i18n import Message
from bs_table_py.table import datetime_format

from web.template_filters import datetime_filter


def format_log_entry(entry, log_type):
    """Format a logentry in correct json

    :param LogEntry entry:
    :param log_type: The logtype to include, currently ``'user'`` or
        ``'room'``.
    """
    return {
        'created_at': datetime_format(entry.created_at, formatter=datetime_filter),
        'raw_created_at': entry.created_at,
        'user': {
            'type': 'native',  # parses it as a link
            'title': entry.author.name,
            'href': url_for("user.user_show", user_id=entry.author.id)
        },
        'message': Message.from_json(entry.message).localize(),
        'type': log_type
    }


format_user_log_entry = partial(format_log_entry, log_type='user')
format_task_log_entry = partial(format_log_entry, log_type='task')
format_room_log_entry = partial(format_log_entry, log_type='room')


def radius_description(interface, entry):
    """Build a readable log message from a radius log entry.

    :param interface: Something whose string representation can be
        used to inform about the port the radius log happened.  For
        instance, this can be a :py:cls:`SwitchPort` object
        formatting itself to `switch-wu5-00 (D15)` or similar.
    :param RadiusLogEntry entry: A :py:cls:`RadiusLogEntry` as
        obtained from a :py:cls:`HadesLogs` lookup.
    """
    prefix = "{port} – {mac} – ".format(port=interface, mac=entry.mac)
    if not entry:
        msg = ("REJECTED - This should never happen!"
               " Please contact a root of your choice.")
    else:
        msg = "Groups: {}, VLANs: {}".format(", ".join(entry.groups),
                                             ", ".join(entry.vlans))
    return prefix + msg


def format_hades_log_entry(interface, entry):
    """Turn Radius Log entry information into a canonical form

    This utilizes :py:func:`radius_description` but returns a dict in
    a format conforming with other log sources' output (consider user
    and room logs)

    :param interface: See :py:func:`radius_description`.
    :param entry: See :py:func:`radius_description`.
    """
    date = entry.time
    desc = radius_description(interface, entry)
    return {
        'created_at': datetime_format(date, formatter=datetime_filter),
        'raw_created_at': date,
        'user': {
            'type': 'plain',  # (w/o link) vs. 'native' (w/ link)
            'title': "Radius",  # or switch name?
        },
        'message': desc,
        'type': 'hades'
    }


def format_custom_hades_message(message):
    date = datetime.now(tz=timezone.utc)
    return {
        'created_at': datetime_format(date, formatter=datetime_filter),
        'raw_created_at': date,
        'user': {
            'type': 'plain',
            'title': "Radius",
        },
        'message': message,
        'type': 'hades'
    }


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
