# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.net
~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations
import typing as t

import ipaddr
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
    address: Mapped[ipaddr._BaseNet]
    gateway: Mapped[ipaddr._BaseIP | None]
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


# Ensure that the gateway is contained in the subnet
constraint = CheckConstraint(Subnet.gateway.op('<<')(Subnet.address))
event.listen(
    Subnet.__table__,
    "after_create",
    AddConstraint(constraint).execute_if(dialect='postgresql')
)
