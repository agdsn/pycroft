from datetime import datetime
from functools import partial

from flask import url_for

from pycroft.helpers.i18n import Message
from web.template_filters import datetime_filter

def format_log_entry(entry, log_type):
    return {
        'created_at': datetime_filter(entry.created_at),
        'raw_created_at': entry.created_at,
        'user': {
            'title': entry.author.name,
            'href': url_for("user.user_show", user_id=entry.author.id)
        },
        'message': Message.from_json(entry.message).localize(),
        'type': log_type
    }


format_user_log_entry = partial(format_log_entry, log_type='user')
format_room_log_entry = partial(format_log_entry, log_type='room')


def _parse_hades_response(response):
    auth_date = response[3]
    msg_parts = ["Authentication of {mac} – ".format(mac=response[2])]
    if response[0].lower() == "auth-reject":
        msg_parts.append(
            "REJECTED – This should never happen!"
            " Please contact a root of your choosing!"
        )
    else:
        group = response[1]
        # TODO: replymessages (resulting auth group)
        # - tagged: "Access granted (tagged)"
        # - untagged: "Access granted (untagged)"
        # - traffic: "Denied (Traffic)"
        # - etc.
        msg_parts.append("Resulting group: {}".format(group))
    return auth_date, "".join(msg_parts)


def format_hades_log_entry(response):
    date, desc = _parse_hades_response(response)
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
