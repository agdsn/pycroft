# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import (
    CheckConstraint, Column, Integer, ForeignKey, String, between, event)
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.orm import relationship, backref
from sqlalchemy.schema import AddConstraint

from pycroft.model.base import ModelBase


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

    private_subnet = relationship(PrivateSubnet, nullable=False, backref=backref("private_subnets"))

    comment = Column(String)


class PrivateSubnet(ModelBase):
    address = Column(CIDR, primary_key=True)

    vid = Column(Integer)

    __table_args = (
        CheckConstraint(between(vid, 1, 4094)),
    )



class PublicIP(ModelBase):
    address = Column(CIDR, primary_key=True)

    owner = relationship(User, backref=backref("public_ips"))


# Ensure that the gateway is contained in the subnet
constraint = CheckConstraint(GlobalSubnet.gateway.op('<<')(GlobalSubnet.address))
event.listen(
    GlobalSubnet.__table__,
    "after_create",
    AddConstraint(constraint).execute_if(dialect='postgresql')
)
