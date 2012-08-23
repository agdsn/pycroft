# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.accounting
~~~~~~~~~~~~~~

This module contains the classes LogEntry, UserLogEntry, TrafficVolume.

:copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Boolean, BigInteger, Enum, Integer, DateTime
from sqlalchemy.types import Text


class TrafficVolume(ModelBase):
    # how many bytes
    size = Column(BigInteger, nullable=False)
    # when this was logged
    timestamp = Column(DateTime, nullable=False)
    type = Column(Enum("IN", "OUT", name="traffic_types"), nullable=False)

    # many to one from TrafficVolume to NetDevice
    ip = relationship("Ip",
                backref=backref("traffic_volumes"))
    ip_id = Column(Integer, ForeignKey("ip.id"), nullable=False)

    net_device = relationship("NetDevice",
        secondary="ip",
        viewonly=True)
