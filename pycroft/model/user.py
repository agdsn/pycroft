# -*- coding: utf-8 -*-
"""
    pycroft.model.user
    ~~~~~~~~~~~~~~

    This module contains the class User.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import DateTime, Integer
from sqlalchemy.types import String


class User(ModelBase):
    login = Column(String(40))
    name = Column(String(255))
    registration_date = Column(DateTime)

    # many to one from User to Room
    room = relationship("Room", backref=backref("users", order_by=id))
    room_id = Column(Integer, ForeignKey("room.id"))
