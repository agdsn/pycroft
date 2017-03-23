# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import BigInteger, Enum, Integer, DateTime
from sqlalchemy.ext.declarative import AbstractConcreteBase

from pycroft.model.base import ModelBase
from pycroft.model.user import User
from pycroft.model.functions import utcnow
from pycroft.model.host import IP, Interface, Host


class TrafficBalance(ModelBase):
    id = None
    user_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                     primary_key=True)
    user = relationship(User,
                        backref=backref("_traffic_balance", uselist=False))
    amount = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, default=utcnow(), nullable=False)


class TrafficEvent(AbstractConcreteBase, ModelBase):
    __table_name__ = None
    timestamp = Column(DateTime, default=utcnow(), nullable=False)
    amount = Column(BigInteger, CheckConstraint('amount >= 0'),
                    nullable=False)


class TrafficVolume(TrafficEvent):
    type = Column(Enum("IN", "OUT", name="traffic_types"),
                  nullable=False)
    ip_id = Column(Integer, ForeignKey(IP.id, ondelete="CASCADE"),
                   nullable=False)
    ip = relationship(IP, backref=backref("traffic_volumes",
                                          cascade="all, delete-orphan"))

    user = relationship(User,
                        secondary="join(Host, Interface,"
                                  "Interface.host_id == Host.id).join(IP)",
                        backref="traffic_volumes",
                        viewonly=True,  # cascade via ip
                        uselist=False)

    __mapper_args__ = {
        'polymorphic_identity': 'traffic_volume',
        'concrete': True,
    }


class TrafficCredit(TrafficEvent):
    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     nullable=False)
    user = relationship(User,
                        backref=backref("traffic_credits",
                                        cascade="all, delete-orphan"),
                        uselist=False)

    __mapper_args__ = {
        'polymorphic_identity': 'traffic_credit',
        'concrete': True,
    }