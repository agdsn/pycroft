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

    # many to one from TrafficVolume to NetDevice
    ip = relationship("IP", backref=backref("traffic_volumes",
                                            cascade="all, delete-orphan"))
    ip_id = Column(Integer, ForeignKey("ip.id", ondelete="CASCADE"),
                   nullable=False)

    net_device = relationship("NetDevice", secondary="ip", viewonly=True)
