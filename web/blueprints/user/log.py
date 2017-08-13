"""
web.blueprints.user.log

This module contains functions that provide certain types of logs for
a user.
"""
from hades_logs import hades_logs, HadesConfigError
from pycroft.model import session

from ..helpers.log import format_hades_log_entry, format_hades_disabled_log


def iter_hades_switch_ports(room):
    """Return all tuples of (nasportid, nasipaddress) for a room.

    :param Room room: The room to filter by

    :returns: An iterator of (nasportid, nasipaddress) usable as
              arguments in ``HadesLogs.fetch_logs()``
    """
    from pycroft.model._all import Room, SwitchPatchPort, SwitchInterface, Switch
    query = (
        session.session
        .query(SwitchInterface.name, Switch.management_ip)
        .join(SwitchPatchPort.room)
        .join(SwitchPatchPort.switch_interface)
        .join(SwitchInterface.host)
        .filter(Room.id == room.id)
    )
    return query.all()


def get_user_hades_logs(user):
    """Iterate over a user's hades logs

    :param User user: the user whose logs to display

    :returns: an iterator over duples (interface, logentry).
    :rtype: Iterator[SwitchInterface, RadiusLogEntry]
    """
    for host in user.user_hosts:
        for patch_port in host.room.switch_patch_ports:
            interface = patch_port.switch_interface
            nasportid = interface.name
            nasipaddress = interface.host.management_ip
            for logentry in hades_logs.fetch_logs(nasipaddress, nasportid):
                yield interface, logentry


def formatted_user_hades_logs(user):
    """Iterate over the user's hades logs if configured correctly

    In case of misconfiguration, i.e. if
    :py:func:`get_user_hades_logs` raises a :py:cls:`RuntimeError`, a
    dummy log entry containing a warning is yielded.

    :param User user: the user whose logs to display

    :returns: an iterator of log rows.  See :py:module:`..helpers.log`
    """
    try:
        for interface, entry in get_user_hades_logs(user):
            yield format_hades_log_entry(interface, entry)
    except HadesConfigError:
        yield format_hades_disabled_log()
        return
