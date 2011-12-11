# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.dormitory
    ~~~~~~~~~~~~~~

    This module contains the classes Dormitory, Room, Subnet, VLan.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Table, Column
#from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Boolean, Integer
from sqlalchemy.types import String


association_table_dormitory_vlan = Table('association_dormitory_vlan',
                                         ModelBase.metadata,
                                         Column('dormitory_id', Integer,
                                                ForeignKey('dormitory.id')),
                                         Column('vlan_id', Integer,
                                                ForeignKey('vlan.id')))


association_table_subnet_vlan = Table("association_subnet_vlan",
                                        ModelBase.metadata,
                                        Column("subnet_id", Integer,
                                                ForeignKey("subnet.id")),
                                        Column("vlan_id", Integer,
                                                ForeignKey("vlan.id")))


class Dormitory(ModelBase):
    number = Column(String(3), unique=True, nullable=False)
    street = Column(String(20), nullable=False)
    short_name = Column(String(5), unique=True, nullable=False)

    #many to many from Dormitory to VLan
    vlans = relationship("VLan",
                            backref=backref("dormitories",
                            secondary=association_table_dormitory_vlan))


class Room(ModelBase):
    number = Column(String(36), nullable=False)
    level = Column(Integer, nullable=False)
    inhabitable = Column(Boolean, nullable=False)

    # many to one from Room to Dormitory
    dormitory_id = Column(Integer, ForeignKey("dormitory.id"), nullable=False)
    dormitory = relationship("Dormitory", backref=backref("rooms",
                                                      order_by=number))

    # one to one from PatchPort to Room
    patch_port_id = Column(Integer, ForeignKey('patchport.id'), nullable=False)
    patch_port = relationship("PatchPort", backref=backref("room",
                                                          uselist=False))


class Subnet(ModelBase):
    #address = Column(postgresql.INET, nullable=False)
    address = Column(String(48), nullable=False)

    #many to many from Subnet to VLan
    vlans = relationship("VLan",
                            backref=backref("subnets",
                            secondary=association_table_subnet_vlan))


class VLan(ModelBase):
    name = Column(String(127), nullable=False)
    tag = Column(Integer, nullable=False)
