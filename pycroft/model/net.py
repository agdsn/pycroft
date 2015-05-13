# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import (
    CheckConstraint, Column, Integer, ForeignKey, String, between, event)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import AddConstraint
from pycroft.model.base import ModelBase
from pycroft.model.types import IPAddress, IPNetwork


class VLAN(ModelBase):
    name = Column(String(127), nullable=False)
    vid = Column(Integer, nullable=False)

    __table_args = (
        CheckConstraint(between(vid, 1, 4094)),
    )


class Subnet(ModelBase):
    address = Column(IPNetwork, nullable=False)
    gateway = Column(IPAddress)
    primary_dns_zone_id = Column(Integer, ForeignKey("dns_zone.id"),
                                 nullable=False)
    primary_dns_zone = relationship("DNSZone", foreign_keys=[primary_dns_zone_id])
    reverse_dns_zone_id = Column(Integer, ForeignKey("dns_zone.id"),
                                 nullable=True)
    reverse_dns_zone = relationship("DNSZone", foreign_keys=[reverse_dns_zone_id])
    reserved_addresses = Column(Integer, default=0, nullable=False)
    description = Column(String(50))

    vlan_id = Column(Integer, ForeignKey(VLAN.id), nullable=False)
    vlan = relationship(VLAN, backref=backref("subnets"))


# Ensure that the gateway is contained in the subnet
constraint = CheckConstraint(Subnet.gateway.op('<<')(Subnet.address))
event.listen(
    Subnet.__table__,
    "after_create",
    AddConstraint(constraint).execute_if(dialect='postgresql')
)
