# -*- coding: utf-8 -*-
"""
    pycroft.model.rights
    ~~~~~~~~~~~~~~

    This module contains the classes Group, Membership, Right.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer, DateTime
from sqlalchemy.types import String


class Group(ModelBase):
    name = Column(String(255))


class Membership(ModelBase):
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey('group.id'), primary_key=True)
    group = relationship("Group", backref=backref("memberships", order_by=id))
    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)
    user = relationship("User", backref=backref("memberships", order_by=id))


class Right(ModelBase):
    name = Column(String(255))

    # many to one from Right to Group
    group_id = Column(Integer, ForeignKey("group.id"))
    group = relationship("Group", backref=backref("rights"))
