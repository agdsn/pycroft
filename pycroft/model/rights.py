# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
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
    discriminator = Column('type', String(17))
    __mapper_args__ = {'polymorphic_on': discriminator}


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

    # many to one from Right to RightGroup
    right_group_id = Column(Integer, ForeignKey("rightgroup.id"))
    right_group = relationship("RightGroup", backref=backref("rights"))


class RightGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'rightgroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True)


class TrafficGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'trafficgroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True)
    # in megabyte
    traffic_limit = Column(Integer)
