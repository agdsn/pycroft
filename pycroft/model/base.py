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
from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base, declared_attr
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
    
    # one to many from User to Host
    user_id = Column(Integer, ForeignKey("user.id"))


class LogEntry(ModelBase):
    # variably sized string
    message = Column(Text)
    # created
    timestamp = Column(DateTime)
    
    # many to one from User to LogEntry
    author_id = Column(Integer, ForeignKey("user.id"))


class Membership(ModelBase):
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    user = relationship("User", backref=backref("memberships", order_by=id))
    group = relationship("Group", backref=backref("memberships", order_by=id))


class NetDevice(ModelBase):
    ipv4 = Column(Sring(12), unique=True)
    ipv6 = Column(String(51), unique=True)
    mac = Column(String(13))
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
 
    # one to many from User to TrafficVolume
    user_id = Column(Integer, ForeignKey("user.id"))


class User(ModelBase):
    login = Column(String(40))
    name = Column(String(255))
    registration_date = Column(DateTime)
  
    # one to many from User to Host
    hosts = relationship("Host")
    # one to many from User to LogEntry
    log_entries = relationship("LogEntry")
    #
    room = relationship("Room", backref=backref("users", order_by=id))
    room_id = Column(Integer, ForeignKey("room.id"))
    # one to many from User to TrafficVolume
    traffic_volumes = relationship("TrafficVolume")
 

class VLan(ModelBase):
    name = Column(String(127))
    tag = Column(Integer)

    # one to one from Dormitory to VLan
    dormitory_id = Column(Integer, ForeignKey("dormitory.id"))
    # one to one from Subnet to VLan
    subnet_id = Column(Integer, ForeignKey("subnet.id"))
