# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import (
    CheckConstraint, Column, Integer, ForeignKey, String, between, event, sql)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import AddConstraint
from pycroft.model.base import IntegerIdModel
from pycroft.model.types import IPAddress, IPNetwork


class VLAN(IntegerIdModel):
    name = Column(String(127), nullable=False)
    vid = Column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(between(vid, 1, 4094)),
    )
    switch_ports = relationship('SwitchPort', secondary='switch_port_default_vlans',
                                back_populates='default_vlans')
    subnets = relationship('Subnet', back_populates='vlan', viewonly=True)


class Subnet(IntegerIdModel):
    address = Column(IPNetwork, nullable=False)
    gateway = Column(IPAddress)
    reserved_addresses_bottom = Column(Integer, server_default=sql.text('0'),
                                       nullable=False)
    reserved_addresses_top = Column(Integer, server_default=sql.text('0'),
                                    nullable=False)
    description = Column(String(50))

    vlan_id = Column(Integer, ForeignKey(VLAN.id), nullable=False, index=True)
    vlan = relationship(VLAN, back_populates="subnets")


# Ensure that the gateway is contained in the subnet
constraint = CheckConstraint(Subnet.gateway.op('<<')(Subnet.address))
event.listen(
    Subnet.__table__,
    "after_create",
    AddConstraint(constraint).execute_if(dialect='postgresql')
)
