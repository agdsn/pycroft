# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.net
~~~~~~~~~~~~~~~
"""
import typing as t

import netaddr
from sqlalchemy import func, and_, cast
from sqlalchemy.orm import Session

from pycroft.lib.exc import PycroftLibException
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.host import IP
from pycroft.model.net import Subnet
from pycroft.model.types import IPAddress

class SubnetFullException(PycroftLibException):
    def __init__(self) -> None:
        super().__init__("Subnet full")


class MacExistsException(PycroftLibException):
    def __init__(self) -> None:
        super().__init__("MAC address already exists")


def get_unused_ips(
    subnets: t.Iterable[Subnet],
) -> dict[Subnet, t.Iterator[netaddr.IPAddress]]:
    import warnings

    warnings.warn(
        "Use `subnet.iter_unused_ips()` instead of `net.get_unused_ips`",
        DeprecationWarning,
        stacklevel=2,
    )
    return {subnet: subnet.unused_ips_iter() for subnet in subnets}


def get_free_ip(subnets: t.Iterable[Subnet]) -> tuple[netaddr.IPAddress, Subnet]:
    try:
        return next((ip, subnet) for subnet in subnets for ip in subnet.unused_ips_iter())
    except StopIteration:
        raise SubnetFullException from None


#TODO: Implement this in the model
def get_subnets_for_room(room: Room) -> list[Subnet]:
    if not room:
        return list()

    return [s for p in room.connected_patch_ports
               for v in p.switch_port.default_vlans
               for s in v.subnets
               if s.address.version == 4]



def calculate_max_ips(subnet: Subnet) -> int:
    import warnings

    warnings.warn(
        "Use `Subnet.usable_size` instead of calculate_max_ips", DeprecationWarning, stacklevel=2
    )
    return subnet.usable_size


class SubnetUsage(t.NamedTuple):
    max_ips: int
    used_ips: int

    @property
    def free_ips(self) -> int:
        return self.max_ips - self.used_ips


def get_subnets_with_usage() -> list[tuple[Subnet, SubnetUsage]]:
    is_unreserved_ip = and_(
        IP.address >= cast(func.host(func.network(
            Subnet.address) + Subnet.reserved_addresses_bottom + 1), IPAddress),
        IP.address <= cast(func.host(
            func.broadcast(Subnet.address) - Subnet.reserved_addresses_top - 1),
            IPAddress)
    )

    subnets_with_used_ips = (
        session.session.query(Subnet, func.count(IP.id).label('used_ips'))
        .outerjoin(IP, and_(IP.subnet_id == Subnet.id, is_unreserved_ip))
        .group_by(Subnet.id)
    ).all()

    return [
        (subnet, SubnetUsage(max_ips=calculate_max_ips(subnet), used_ips=used_ips))
        for subnet, used_ips in subnets_with_used_ips
    ]


def delete_ip(session: Session, ip: netaddr.IPAddress) -> None:
    # TODO use proper `delete` statement
    session.delete(IP.q.filter_by(address=ip).first())
