# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
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


class Dormitory(ModelBase):
    number = Column(String(3), unique=True)
    street = Column(String(20))
    short_name = Column(String(5), unique=True)

    # one to one from Dormitory to VLan
    v_lan = relationship("VLan", uselist=False, backref="dormitory")


class Group(ModelBase):
    name = Column(String(255))


class Host(ModelBase):
    hostname = Column(String(255))

    # many to one from Host to User
    user = relationship("User", backref=backref("hosts", order_by=id))
    user_id = Column(Integer, ForeignKey("user.id"))


class LogEntry(ModelBase):
    # variably sized string
    message = Column(Text)
    # created
    timestamp = Column(DateTime)

    # many to one from LogEntry to User
    author = relationship("User", \
                backref=backref("log_entries", order_by=timestamp))
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
    address = Column(String(48))
    #address = Column(postgresql.INET)

    # one to one from Subnet to VLan
    v_lan = relationship("VLan", uselist=False, backref="subnet")


class TrafficVolume(ModelBase):
    # 1 (true) for in, 0 (false) for out
    direction = Column(Boolean)
    # how many bytes
    size = Column(BigInteger)
    # when this was logged
    timestamp = Column(DateTime)

    # many to one from LogEntry to User
    user = relationship("User", \
                backref=backref("traffic_volumes", order_by=timestamp))
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

    # one to one from Dormitory to VLan
    dormitory_id = Column(Integer, ForeignKey("dormitory.id"))
    # one to one from Subnet to VLan
    subnet_id = Column(Integer, ForeignKey("subnet.id"))
