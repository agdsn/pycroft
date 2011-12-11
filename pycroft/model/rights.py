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
from sqlalchemy.types import BigInteger, Integer, DateTime
from sqlalchemy.types import String


class Group(ModelBase):
    name = Column(String(255), nullable=False)
    discriminator = Column('type', String(17), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}


class Membership(ModelBase):
    start_date = Column(DateTime)
    end_date = Column(DateTime, nullable=True)

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                        nullable=False)
    group = relationship("Group", backref=backref("memberships", order_by=id))
    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True,
                        nullable=False)
    user = relationship("User", backref=backref("memberships", order_by=id))


class Right(ModelBase):
    name = Column(String(255), nullable=False)

    # many to one from Right to RightGroup
    # nullable=True
    right_group_id = Column(Integer, ForeignKey("rightgroup.id"),
                            nullable=False)
    right_group = relationship("RightGroup", backref=backref("rights"))


class RightGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'rightgroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                nullable=False)


class TrafficGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'trafficgroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                nullable=False)
    # in byte per seven days, zero is no limit
    traffic_limit = Column(BigInteger, nullable=False)
