# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.accounting
~~~~~~~~~~~~~~

This module contains the classes TrafficVolume and TrafficCredit. Both are used
to account the consumed traffic of a user.

:copyright: (c) 2011 by AG DSN.
"""
import datetime

from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import BigInteger, Enum, Integer, DateTime
from pycroft.model.base import ModelBase


class TrafficVolume(ModelBase):
    """This is represents a volume of traffic consumption within a fixed
    interval

    The sum of all the volumes within a given time will be the overall
    traffic consumption. The counting goes per ip and per direction.
    """

    # how many bytes
    size = Column(BigInteger, nullable=False)
    # when this was logged
    timestamp = Column(DateTime, nullable=False)
    traffic_type = Column(Enum("IN", "OUT", name="traffic_types"), nullable=False)

    # many to one from TrafficVolume to Interface
    ip = relationship("IP", backref=backref("traffic_volumes",
                                            cascade="all, delete-orphan"))
    ip_id = Column(Integer, ForeignKey("ip.id", ondelete="CASCADE"),
                   nullable=False)

    interface = relationship("Interface", secondary="ip", viewonly=True)


class TrafficCredit(ModelBase):
    """Represents the traffic credit the user has.

    Only the newest value should be used for accounting. The older ones are only
    kept for reporting purposes. The granted amount means the sum of inbound
    and outbound traffic. To distinguish between the direction do it by
    manipulating the consumption parts.
    """
    grant_date = Column(DateTime, default=datetime.datetime.now, nullable=False)

    # ToDo JanLo: Test Cascade
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User",
                        backref=backref("traffic_credits",
                                        cascade="all, delete-orphan",
                                        order_by="TrafficCredit.grant_date"))


    amount = Column(BigInteger, nullable=False)
    added_amount = Column(BigInteger, nullable=False)
