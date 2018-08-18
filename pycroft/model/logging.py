# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.logging
    ~~~~~~~~~~~~~~

    This module contains the classes LogEntry, UserLogEntry, TrafficVolume.

    :copyright: (c) 2011 by AG DSN.
"""
from sqlalchemy import Column, ForeignKey, func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer, Text, String
from pycroft.model.base import IntegerIdModel
from pycroft.model.types import DateTimeTz


class LogEntry(IntegerIdModel):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    # variably sized string
    message = Column(Text, nullable=False)
    # created
    created_at = Column(DateTimeTz, nullable=False, server_default=func.current_timestamp())

    # many to one from LogEntry to User
    author = relationship("User",
                          backref=backref("authored_log_entries"))
    author_id = Column(Integer, ForeignKey("user.id"), index=True)


class UserLogEntry(LogEntry):
    __mapper_args__ = {'polymorphic_identity': 'user_log_entry'}
    id = Column(Integer, ForeignKey(LogEntry.id, ondelete="CASCADE"),
                primary_key=True)

    # many to one from UserLogEntry to User
    user = relationship("User", backref=backref("log_entries",
                                                cascade="all, delete-orphan"))
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"),
                     nullable=False, index=True)


class RoomLogEntry(LogEntry):
    __mapper_args__ = {'polymorphic_identity': 'room_log_entry'}
    id = Column(Integer, ForeignKey('log_entry.id'), primary_key=True)

    # many to one from RoomLogEntry to Room
    room = relationship("Room", backref=backref("log_entries"))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False, index=True)
