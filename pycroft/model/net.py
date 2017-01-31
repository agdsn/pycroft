# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import (
    CheckConstraint, Column, Integer, ForeignKey, String, between, event)
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import AddConstraint

from pycroft.model.base import ModelBase
from pycroft.model.host import NAS
from pycroft.model.user import User


class GlobalVLAN(ModelBase):
    name = Column(String(127), nullable=False)
    vid = Column(Integer, nullable=False)

    comment = Column(String)

    __table_args = (
        CheckConstraint(between(vid, 1, 4094)),
    )


class GlobalSubnet(ModelBase):
    address = Column(CIDR, nullable=False)
    gateway = Column(CIDR)
    reserved_addresses = Column(Integer, default=0, nullable=True)
    description = Column(String(50))

    vlan_id = Column(Integer, ForeignKey(GlobalVLAN.id), nullable=False)
    vlan = relationship(GlobalVLAN, backref=backref("subnets"))


class Translation(ModelBase):
    public_ip = relationship(PublicIP, nullable=False, backref=backref("translations"))

    translated_net = Column(CIDR, nullable=False)
    private_subnet = relationship(PublicIP,
                           primaryjoin="translation.translated_net.op('<<=', is_comparison=True)"
                                       "(foreign(private_subnet.cidr))",
                           viewonly=True)

    comment = Column(String)

    # might be null for office networks or similar constructs
    owner_id = Column(Integer, ForeignKey(User.id), nullable=True)
    owner = relationship(User, nullable=True, backref=backref("public_ips"))


class PrivateSubnet(ModelBase):
    cidr = Column(CIDR, primary_key=True)

    vid = Column(Integer)

    router_id = Column(Integer, ForeignKey(NAS.id), nullable=False)
    router = relationship(NAS, nullable=False, backref=backref("private_subnets"))

    __table_args = (
        CheckConstraint(between(vid, 2048, 4096)),
    )



class PublicIP(ModelBase):
    address = Column(INET, primary_key=True)


# Ensure that the gateway is contained in the subnet
constraint = CheckConstraint(GlobalSubnet.gateway.op('<<')(GlobalSubnet.address))
event.listen(
    GlobalSubnet.__table__,
    "after_create",
    AddConstraint(constraint).execute_if(dialect='postgresql')
)
