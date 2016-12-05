# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.accounting
~~~~~~~~~~~~~~

This module contains the classes LogEntry, UserLogEntry, TrafficVolume.

:copyright: (c) 2011 by AG DSN.
"""
from sqlalchemy import Column, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import BigInteger, Enum, Integer, DateTime
from sqlalchemy.ext.declarative import AbstractConcreteBase
from pycroft.model.base import ModelBase
from pycroft.model.user import User
from pycroft.model.functions import utcnow
from pycroft.model.host import IP, Interface, Host


class TrafficBalance(ModelBase):
    __tablename__ = 'traffic_balance'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey(User.id), unique=True)
    user = relationship(User,
                        backref=backref("_traffic_balance", uselist=False))
    balance = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=utcnow(), nullable=False)


class TrafficEvent(AbstractConcreteBase, ModelBase):
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=utcnow(), nullable=False)
    amount = Column('amount', BigInteger, nullable=False)


class TrafficDebit(TrafficEvent):
    __tablename__ = 'traffic_debit'
    traffic_type = Column(Enum("IN", "OUT", name="traffic_types"),
                          nullable=False)

    ip_id = Column(Integer, ForeignKey(IP.id))
    ip = relationship(IP)

    user = relationship(User,
                        secondary="join(Host, Interface,"
                                  "Interface.host_id == Host.id).join(IP)",
                        backref=backref("traffic_debit",
                                        cascade="all"),  # delete-orphan
                        uselist=False)

    __table_args__ = (CheckConstraint('amount<=0'),)
    __mapper_args__ = {
        'polymorphic_identity': 'traffic_debit',
        'concrete': True,
    }


class TrafficCredit(TrafficEvent):
    __tablename__ = 'traffic_credit'
    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'))
    user = relationship(User,
                        backref=backref("traffic_credit",
                                        cascade="all, delete-orphan"),
                        uselist=False)

    __table_args__ = (CheckConstraint('amount>=0'),)
    __mapper_args__ = {
        'polymorphic_identity': 'traffic_credit',
        'concrete': True,
    }