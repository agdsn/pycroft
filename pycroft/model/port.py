# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from pycroft.model.base import IntegerIdModel
from pycroft.model.facilities import Room
from pycroft.model.host import SwitchPort


class PatchPort(IntegerIdModel):
    """A patch panel port that may or not be connected to a switch"""
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False, index=True)
    name = Column(String(8), nullable=False)

    switch_port_id = Column(Integer, ForeignKey(SwitchPort.id), unique=True)
    switch_port = relationship(SwitchPort,
                               backref=backref("patch_port", uselist=False))

    room = relationship(Room, back_populates="patch_ports")
