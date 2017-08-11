from datetime import datetime
from functools import partial

from flask import url_for

from pycroft.helpers.i18n import Message
from web.template_filters import datetime_filter


def format_log_entry(entry, log_type):
    """Format a logentry in correct json

    :param LogEntry entry:
    :param log_type: The logtype to include, currently ``'user'`` or
        ``'room'``.
    """
    return {
        'created_at': datetime_filter(entry.created_at),
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
format_room_log_entry = partial(format_log_entry, log_type='room')


def radius_description(interface, entry):
    """Build a readable log message from a radius log entry.

    :param interface: Something whose string representation can be
        used to inform about the port the radius log happened.  For
        instance, this can be a :py:cls:`SwitchInterface` object
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
        'created_at': datetime_filter(date),
        'raw_created_at': date,
        'user': {
            'type': 'plain',  # (w/o link) vs. 'native' (w/ link)
            'title': "Radius",  # or switch name?
        },
        'message': desc,
        'type': 'hades'
    }


test_hades_logs = [
    ("Auth-Reject", "", "00:de:ad:be:ef:00", datetime(2017, 5, 20, 18, 25), None),
    ("Auth-Access", "Wu5_untagged", "00:de:ad:be:ef:00", datetime(2017, 4, 20, 18, 20), 15),
    ("Auth-Access", "unknown", "00:de:ad:be:ef:01", datetime(2017, 4, 20, 18, 5), 1001),
    ("Auth-Access", "traffic", "00:de:ad:be:ef:00", datetime(2017, 4, 20, 18, 0), 1001),
]
