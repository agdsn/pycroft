# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
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
from sqlalchemy.types import Boolean, BigInteger, Integer, DateTime
from sqlalchemy.types import Text


class TrafficVolume(ModelBase):
    incoming = Column(Boolean)
    # how many bytes
    size = Column(BigInteger)
    # when this was logged
    timestamp = Column(DateTime)

    # many to one from LogEntry to User
    user = relationship("User",
                backref=backref("traffic_volumes"))
    user_id = Column(Integer, ForeignKey("user.id"))

class TrafficLimit(ModelBase):
    # in megabyte
    size= Column(Integer)
