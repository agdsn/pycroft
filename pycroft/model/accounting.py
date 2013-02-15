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
import datetime

from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import BigInteger, Enum, Integer, DateTime
from pycroft.model.base import ModelBase


class TrafficVolume(ModelBase):
    # how many bytes
    size = Column(BigInteger, nullable=False)
    # when this was logged
    timestamp = Column(DateTime, nullable=False)
    type = Column(Enum("IN", "OUT", name="traffic_types"), nullable=False)

    # many to one from TrafficVolume to Interface
    ip = relationship("IP", backref=backref("traffic_volumes",
                                            cascade="all, delete-orphan"))
    ip_id = Column(Integer, ForeignKey("ip.id", ondelete="CASCADE"),
                   nullable=False)

    interface = relationship("Interface", secondary="ip", viewonly=True)


class TrafficCredit(ModelBase):
    """Represents the traffic credit the user has.

    Only the newes value should be used for accounting. The older ones are only
    kept for reporting purposes.

    """
    user = relationship("User", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)

    grant_date = Column(DateTime, default=datetime.datetime.now, nullable=False)

    amount = Column(BigInteger, nullable=False)
    added_amount = Column(BigInteger, nullable=False)
