# -*- coding: utf-8 -*-
"""
    pycroft.model.base
    ~~~~~~~~~~~~~~

    This module contains base stuff for all models.

    :copyright: (c) 2011 by AG DSN.
"""
from sqlalchemy import ForeignKey, MetaData
from sqlalchemy import Table, Column
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import BigInteger, Boolean, DateTime, Integer
from sqlalchemy.types import Text, String

_session = None


class _ModelMeta(DeclarativeMeta):
    """Metaclass for all mapped Database objects.
    """
    @property
    def q(cls):
        """This is a shortcut for easy querying of whole objects.

        With this metaclass shortcut you can query a Model with
        Model.q.filter(...) without using the verbose session stuff
        """
        global _session
        if _session is None:
            import pycroft.model.session
            _session = pycroft.model.session.session
        return _session.query(cls)


class _Base(object):
    """Baseclass for all database models.
    """
    id = Column(Integer, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        """Autogenerate the tablename for the mapped objects.

        """
        return cls.__name__.lower()


ModelBase = declarative_base(cls=_Base, metaclass=_ModelMeta)

association_table_dormitory_vlan = Table('association_dormitory_vlan',
                                         ModelBase.metadata,
                                         Column('dormitory_id', Integer,
                                                ForeignKey('dormitory.id')),
                                         Column('vlan_id', Integer,
                                                ForeignKey('vlan.id')))

association_table_subnet_vlan = Table('association_subnet_vlan',
                                        ModelBase.metadata,
                                        Column('subnet_id', Integer,
                                                ForeignKey('subnet.id')),
                                        Column("vlan_id", Integer,
                                                ForeignKey('vlan.id')))


class DestinationPort(ModelBase):
    name = Column(String(4))

    # review relation destinationport-patchport
    # and double-relation switchport
    switchport_id = Column(Integer, ForeignKey("switchport.id"))
    phoneport_id = Column(Integer, ForeignKey("phoneport.id"))
    

class Dormitory(ModelBase):
    number = Column(String(3), unique=True)
    street = Column(String(20))
    short_name = Column(String(5), unique=True)

    #many to many from Dormitory to VLan
    vlans = relationship("VLan",
                            backref=backref("dormitories",
                            secondary=association_table_dormitory_vlan))


class Group(ModelBase):
    name = Column(String(255))


class Host(ModelBase):
    hostname = Column(String(255))

    # many to one from Host to User
    user = relationship("User", backref=backref("hosts"))
    user_id = Column(Integer, ForeignKey("user.id"))

    switch_id = Column(Integer, ForeignKey("switch.id"))


class LogEntry(ModelBase):
    # variably sized string
    message = Column(Text)
    # created
    timestamp = Column(DateTime)

    # many to one from LogEntry to User
    author = relationship("User",
                backref=backref("log_entries"))
    author_id = Column(Integer, ForeignKey("user.id"))


class Membership(ModelBase):
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    user = relationship("User", backref=backref("memberships", order_by=id))
    group = relationship("Group", backref=backref("memberships", order_by=id))


class NetDevice(ModelBase):
    #ipv4 = Column(postgresql.INET);
    ipv4 = Column(String(12), unique=True)
    #ipv6 = Column(postgresql.INET);
    ipv6 = Column(String(51), unique=True)
    mac = Column(String(12))
    #mac = Column(postgresql.MACADDR)
    patch_port_id = Column(Integer, ForeignKey("patchport.id"))


class PatchPort(ModelBase):
    name = Column(String(4))


class PhonePort(ModelBase):
    name = Column(String(4))


class Rights(ModelBase):
    name = Column(String(255))


class Room(ModelBase):
    number = Column(String(36))
    level = Column(Integer)
    inhabitable = Column(Boolean)
    dormitory_id = Column(Integer, ForeignKey("dormitory.id"))

    dormitory = relationship("Dormitory", backref=backref("rooms",
                                                      order_by=number))


class Subnet(ModelBase):
    #address = Column(postgresql.INET)
    address = Column(String(48))

    #many to many from Subnet to VLan
    vlans = relationship("VLan",
                            backref=backref("subnets",
                            secondary=association_table_subnet_vlan))


class Switch(ModelBase):
    name = Column(String(4))

    # review double-relation switchport (variable?)
    switchport_id = Column(Integer, ForeignKey("switchport.id"))


class SwitchPort(ModelBase):
    name = Column(String(4))


class TrafficVolume(ModelBase):
    incoming = Column(Boolean)
    # how many bytes
    size = Column(BigInteger)
    # when this was logged
    timestamp = Column(DateTime)

    # many to one from LogEntry to User
    user = relationship("User",
                backref=backref("traffic_volumes"))
    user_id = Column(Integer, ForeignKey("user.id"))


class User(ModelBase):
    login = Column(String(40))
    name = Column(String(255))
    registration_date = Column(DateTime)

    # many to one from User to Room
    room = relationship("Room", backref=backref("users", order_by=id))
    room_id = Column(Integer, ForeignKey("room.id"))


class VLan(ModelBase):
    name = Column(String(127))
    tag = Column(Integer)
