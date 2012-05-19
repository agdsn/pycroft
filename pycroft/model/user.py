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
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import DateTime, Integer
from sqlalchemy.types import String
import re



class User(ModelBase):
    login = Column(String(40), nullable=False)
    name = Column(String(255), nullable=False)
    registration_date = Column(DateTime, nullable=False)

    # many to one from User to Room
    room = relationship("Room", backref=backref("users", order_by='User.id'))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False)

    login_regex = re.compile("^[a-z][a-z0-9_]{1,20}[a-z0-9]$")
    name_regex = re.compile("^(([a-z]{1,5}|[A-Z][a-z0-9]+)\\s)*([A-Z][a-z0-9]+)((-|\\s)"\
                            "[A-Z][a-z0-9]+|\\s[a-z]{1,5})*$")

    @validates('login')
    def validate_login(self, key, value):
        if not User.login_regex.match(value):
            raise Exception("invalid unix-login!")
        return value
