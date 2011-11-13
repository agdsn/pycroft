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

from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base, declared_attr
from sqlalchemy import Integer, String, MetaData, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relation, backref
from sqlalchemy import Table, Column


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

    @declared_attr
    def __tablename__(cls):
        """Autogenerate the tablename for the mapped objects.

        """
        return cls.__name__.lower()



ModelBase = declarative_base(cls=_Base, metaclass=_ModelMeta)



class Dormitory(ModelBase):
    id = Column(Integer, primary_key=True)
    number = Column(String(3), unique=True)
    street = Column(String(20))
    short_name = Column(String(5), unique=True)


class Room(ModelBase):
    id = Column(Integer, primary_key=True)
    number = Column(String(36))
    level = Column(Integer)
    inhabitable = Column(Boolean)
    dormitory_id = Column(Integer, ForeignKey("dormitory.id"))

    dormitory = relation("Dormitory", backref=backref("rooms",
                                                      order_by=number))


class User(ModelBase):
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    login = Column(String(40))
    registration_date = Column(DateTime)
    room_id = Column(Integer, ForeignKey("room.id"))

    room = relation("Room", backref=backref("users", order_by=id))

class Host(ModelBase):
    id = Column(Integer, primary_key=True)
    hostname = Column(String(255))    
