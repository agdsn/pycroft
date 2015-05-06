# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import ipaddr
from sqlalchemy import Column, Enum, Integer, ForeignKey, String, Table
from sqlalchemy.orm import relationship, backref
from pycroft.model.base import ModelBase


class VLAN(ModelBase):
    name = Column(String(127), nullable=False)
    tag = Column(Integer, nullable=False)


class Subnet(ModelBase):
    #address = Column(postgresql.INET, nullable=False)
    address = Column(String(51), nullable=False)
    #gateway = Column(postgresql.INET, nullable=False)
    gateway = Column(String(51), nullable=False)
    dns_domain = Column(String)
    reserved_addresses = Column(Integer, default=0, nullable=False)
    ip_type = Column(Enum("4", "6", name="subnet_ip_type"), nullable=False)
    description = Column(String(50))

    # many to many from Subnet to VLAN
    vlans = relationship(VLAN, backref=backref("subnets"),
                         secondary=lambda: association_table_subnet_vlan)

    @property
    def netmask(self):
        net = ipaddr.IPNetwork(self.address)
        return str(net.netmask)

    @property
    def ip_version(self):
        return ipaddr.IPNetwork(self.address).version


association_table_subnet_vlan = Table(
    "association_subnet_vlan",
    ModelBase.metadata,
    Column("subnet_id", Integer, ForeignKey(Subnet.id)),
    Column("vlan_id", Integer, ForeignKey(VLAN.id)))
