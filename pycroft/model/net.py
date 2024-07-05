# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.net
~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations
import typing as t

import netaddr
from sqlalchemy import CheckConstraint, ForeignKey, between, event, sql
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.schema import AddConstraint

from pycroft.model.base import IntegerIdModel
from pycroft.model.type_aliases import str127, str50

if t.TYPE_CHECKING:
    # backrefs
    from .host import IP

class VLAN(IntegerIdModel):
    name: Mapped[str127]
    vid: Mapped[int] = mapped_column()

    __table_args__ = (CheckConstraint(between(vid, 1, 4094)),)
    # associations
    switch_ports = relationship(
        "SwitchPort",
        secondary="switch_port_default_vlans",
        back_populates="default_vlans",
    )
    # /associations

    # backrefs
    subnets = relationship('Subnet', back_populates='vlan', viewonly=True)
    # /backrefs


class Subnet(IntegerIdModel):
    address: Mapped[netaddr.IPNetwork]
    gateway: Mapped[netaddr.IPAddress | None]
    reserved_addresses_bottom: Mapped[int] = mapped_column(server_default=sql.text("0"))
    reserved_addresses_top: Mapped[int] = mapped_column(server_default=sql.text("0"))
    description: Mapped[str50 | None]

    vlan_id: Mapped[int] = mapped_column(ForeignKey(VLAN.id), index=True)
    vlan: Mapped[VLAN] = relationship(back_populates="subnets")

    # backrefs
    ips: Mapped[list[IP]] = relationship(
        cascade="all, delete-orphan",
        back_populates="subnet",
    )
    # /backrefs

    @property
    def usable_ip_range(self) -> netaddr.IPRange | None:
        """All IPs in this subnet which are not reserved."""
        # takes care of host- and broadcast domains plus edge-cases (e.g. /32)
        first_usable, last_usable = self.address._usable_range()

        res_bottom = self.reserved_addresses_bottom or 0
        res_top = self.reserved_addresses_top or 0
        first_usable = first_usable + res_bottom
        last_usable = last_usable + res_top
        if last_usable < first_usable:
            return None
        return netaddr.IPRange(first_usable, last_usable)

    @property
    def usable_size(self) -> int:
        """The number of IPs in this subnet which are not reserved."""
        return self.usable_ip_range.size if self.usable_ip_range else 0

    def unused_ips_iter(self) -> t.Iterator[netaddr.IPAddress]:
        if not self.usable_ip_range:
            return iter(())
        used_ips = frozenset(ip.address for ip in self.ips)
        return (ip for ip in self.usable_ip_range if ip not in used_ips)


# Ensure that the gateway is contained in the subnet
constraint = CheckConstraint(Subnet.gateway.op('<<')(Subnet.address))
event.listen(
    Subnet.__table__,
    "after_create",
    AddConstraint(constraint).execute_if(dialect='postgresql')
)
