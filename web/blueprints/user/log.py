"""
web.blueprints.user.log

This module contains functions that provide certain types of logs for
a user.
"""
import logging
import typing as t

from netaddr import IPAddress
from sqlalchemy import select, Row
from sqlalchemy.orm import Query

from hades_logs import hades_logs, RadiusLogEntry
from hades_logs.exc import HadesConfigError, HadesOperationalError, HadesTimeout
from pycroft.model import session
from pycroft.model.host import SwitchPort, Switch
from pycroft.model.port import PatchPort
from pycroft.model.user import User
from pycroft.model.facilities import Room
from ..helpers.log import format_hades_log_entry, format_hades_disabled, \
    format_user_not_connected, format_hades_error, format_hades_timeout
from ..helpers.log_tables import LogTableRow

logger = logging.getLogger(__name__)

def iter_hades_switch_ports(room: Room) -> t.Sequence[Row[tuple[str, IPAddress]]]:
    """Return all tuples of (nasportid, nasipaddress) for a room.

    :param room: The room to filter by

    :returns: An iterator of (nasportid, nasipaddress) usable as
              arguments in ``HadesLogs.fetch_logs()``
    """
    stmt = (
        select(SwitchPort.name, Switch.management_ip)
        .join(PatchPort.room)
        .join(PatchPort.switch_port)
        .join(SwitchPort.switch)
        .filter(Room.id == room.id)
    )
    return session.session.execute(stmt).all()


def get_user_hades_logs(user: User) -> t.Iterator[tuple[PatchPort, RadiusLogEntry]]:
    """Iterate over a user's hades logs

    :param user: the user whose logs to display

    :returns: an iterator over duples (interface, log_entry).
    """
    # Accessing the `hades_logs` proxy early ensures the exception is
    # raised even if there's no SwitchPort

    do_fetch = hades_logs.fetch_logs
    q: Query = session.session.query(SwitchPort)
    ports = (
        q
        .join(PatchPort)
        .join(PatchPort.room)
        .join(User)
        .filter(User.id == user.id)
        .distinct()
     )
    for port in ports:
        for log_entry in do_fetch(str(port.switch.management_ip), port.name):
            yield port, log_entry


def is_user_connected(user: User) -> bool:
    try:
        next(patch_port
             for host in user.hosts
             for patch_port in host.room.connected_patch_ports)
    except StopIteration:
        return False
    return True


def formatted_user_hades_logs(user: User) -> t.Iterator[LogTableRow]:
    """Iterate over the user's hades logs if configured correctly

    In case of misconfiguration, i.e. if
    :py:func:`get_user_hades_logs` raises a :class:`RuntimeError`, a
    dummy log entry containing a warning is yielded.

    :param User user: the user whose logs to display

    :returns: an iterator of log rows.  See :py:module:`..helpers.log`
    """
    try:
        for interface, entry in get_user_hades_logs(user):
            yield format_hades_log_entry(interface, entry)
    except HadesConfigError as e:
        logger.error("Error in hades config: %s", e, exc_info=True)
        yield format_hades_disabled()
        return
    except HadesOperationalError as e:
        logger.error("Operational error when fetching hades logs: %s", e, exc_info=True)
        yield format_hades_error()
    except HadesTimeout:
        yield format_hades_timeout()

    if not is_user_connected(user):
        yield format_user_not_connected()
