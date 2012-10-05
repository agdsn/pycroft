# -*- coding: utf-8 -*-
"""
    pycroft.model.dormitory
    ~~~~~~~~~~~~~~

    This module contains the classes Dormitory, Room, Subnet, VLan.

    :copyright: (c) 2011 by AG DSN.
"""

#from sqlalchemy.dialects import postgresql
from base import ModelBase
from pycroft.model.session import session
from sqlalchemy import ForeignKey
from sqlalchemy import Table, Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Boolean, Integer, String, Enum
import ipaddr


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
    short_name = Column(String(5), unique=True, nullable=False)
    street = Column(String(20), nullable=False)

    #many to many from Dormitory to VLan
    vlans = relationship("VLan",
        backref=backref("dormitories"),
        secondary=association_table_dormitory_vlan)

    # methods

    def get_subnets(self):
    #ToDo: Ugly, but ... Someone can convert this is
    #      a proper property of Dormitory
    #ToDo: Also possibly slow and untested
        return session.query(
            Subnet
        ).join(
            Subnet.vlans
        ).join(
            VLan.dormitories
        ).filter(
            Dormitory.id == self.id
        ).all()

    def __repr__(self):
        return u"%s %s" % (self.street, self.number)


class Room(ModelBase):
    number = Column(String(36), nullable=False)
    level = Column(Integer, nullable=False)
    inhabitable = Column(Boolean, nullable=False)

    # many to one from Room to Dormitory
    dormitory_id = Column(Integer, ForeignKey("dormitory.id"), nullable=False)
    dormitory = relationship("Dormitory", backref=backref("rooms"))

    def __repr__(self):
        return u"%s %d%s" % (self.dormitory, self.level, self.number)


class Subnet(ModelBase):
    #address = Column(postgresql.INET, nullable=False)
    address = Column(String(51), nullable=False)
    #gateway = Column(postgresql.INET, nullable=False)
    gateway = Column(String(51), nullable=False)
    dns_domain = Column(String)
    reserved_addresses = Column(Integer, default=0, nullable=False)
    ip_type = Column(Enum("4", "6", name="iptypes"), nullable=False)

    #many to many from Subnet to VLan
    vlans = relationship("VLan",
        backref=backref("subnets"),
        secondary=association_table_subnet_vlan)

    @property
    def netmask(self):
        net = ipaddr.IPNetwork(self.address)
        return str(net.netmask)

    @property
    def ip_version(self):
        return ipaddr.IPNetwork(self.address).version


class VLan(ModelBase):
    name = Column(String(127), nullable=False)
    tag = Column(Integer, nullable=False)
