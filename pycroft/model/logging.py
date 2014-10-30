# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.logging
    ~~~~~~~~~~~~~~

    This module contains the classes LogEntry, UserLogEntry, TrafficVolume.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer, DateTime, Text, String


class LogEntry(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    # variably sized string
    message = Column(Text, nullable=False)
    # created
    timestamp = Column(DateTime, nullable=False)

    # many to one from LogEntry to User
    author = relationship("User",
                          backref=backref("log_entries"))
    author_id = Column(Integer, ForeignKey("user.id"), nullable=False)


class UserLogEntry(LogEntry):
    __mapper_args__ = {'polymorphic_identity': 'user_log_entry'}
    id = Column(Integer, ForeignKey('log_entry.id'), primary_key=True)

    # many to one from UserLogEntry to User
    user = relationship("User", backref=backref("user_log_entries"))
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)


class RoomLogEntry(LogEntry):
    __mapper_args__ = {'polymorphic_identity': 'room_log_entry'}
    id = Column(Integer, ForeignKey('log_entry.id'), primary_key=True)

    # many to one from RoomLogEntry to Room
    room = relationship("Room", backref=backref("room_log_entries"))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False)
