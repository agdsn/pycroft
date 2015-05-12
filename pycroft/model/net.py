# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import ipaddr
from sqlalchemy import Column, Enum, Integer, ForeignKey, String, Table, event
from sqlalchemy.orm import relationship, backref, object_session
from pycroft.lib.net import MacExistsException
from pycroft.model.base import ModelBase
from pycroft.model.host import Interface, IP
from pycroft.model.types import IPAddress, IPNetwork


class VLAN(ModelBase):
    name = Column(String(127), nullable=False)
    tag = Column(Integer, nullable=False)

    dormitories = relationship(
        "Dormitory", backref=backref("vlans"),
        secondary=lambda: association_table_dormitory_vlan)


association_table_dormitory_vlan = Table(
    'association_dormitory_vlan',
    ModelBase.metadata,
    Column('dormitory_id', Integer, ForeignKey('dormitory.id')),
    Column('vlan_id', Integer, ForeignKey(VLAN.id)))


class Subnet(ModelBase):
    address = Column(IPNetwork, nullable=False)
    gateway = Column(IPAddress)
    primary_dns_zone_id = Column(Integer, ForeignKey("dns_zone.id"),
                                 nullable=False)
    primary_dns_zone = relationship("DNSZone", foreign_keys=[primary_dns_zone_id])
    reverse_dns_zone_id = Column(Integer, ForeignKey("dns_zone.id"),
                                 nullable=False)
    reverse_dns_zone = relationship("DNSZone", foreign_keys=[reverse_dns_zone_id])
    reserved_addresses = Column(Integer, default=0, nullable=False)
    description = Column(String(50))

    # many to many from Subnet to VLAN
    vlans = relationship(VLAN, backref=backref("subnets"),
                         secondary=lambda: association_table_subnet_vlan)


association_table_subnet_vlan = Table(
    "association_subnet_vlan",
    ModelBase.metadata,
    Column("subnet_id", Integer, ForeignKey(Subnet.id)),
    Column("vlan_id", Integer, ForeignKey(VLAN.id)))
