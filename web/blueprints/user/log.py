"""
web.blueprints.user.log

This module contains functions that provide certain types of logs for
a user.
"""
from hades_logs import hades_logs
from pycroft.model import session

from ..helpers.log import format_hades_log_entry


def iter_hades_switch_ports(room):
    """Return all tuples of (nasportid, nasipaddress) for a room.

    :param Room room: The room to filter by

    :returns: An iterator of (nasportid, nasipaddress) usable as
              arguments in ``HadesLogs.fetch_logs()``
    """
    # TODO: use this in the Room's view
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
    try:
        log_fetcher = hades_logs.fetch_logs
    except RuntimeError:
        return

    for host in user.user_hosts:
        for patch_port in host.room.switch_patch_ports:
            interface = patch_port.switch_interface
            nasportid = interface.name
            nasipaddress = interface.host.management_ip
            for logentry in log_fetcher(nasipaddress, nasportid):
                yield interface, logentry


def formatted_user_hades_logs(user):
    return (format_hades_log_entry(interface, entry)
            for interface, entry in get_user_hades_logs(user))
