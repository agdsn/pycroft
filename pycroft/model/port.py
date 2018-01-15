# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, backref
from pycroft.model.base import ModelBase
from pycroft.model.facilities import Room
from pycroft.model.host import SwitchPort


class PatchPort(ModelBase):
    """A patch panel port that's not connected"""
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False)
    type = Column(String(20))
    name = Column(String(8), nullable=False)

    __mapper_args__ = {
        'polymorphic_identity': 'unwired_patch_port',
        'polymorphic_on': type
    }


class SwitchPatchPort(PatchPort):
    """A patch panel port connected to a switch port"""
    id = Column(Integer, ForeignKey(PatchPort.id), primary_key=True)

    switch_port_id = Column(Integer, ForeignKey(SwitchPort.id),
                            nullable=False, unique=True)
    switch_port = relationship(SwitchPort,
                               backref=backref("patch_port", uselist=False))
    room = relationship(Room, backref=backref("switch_patch_ports"))

    __mapper_args__ = {'polymorphic_identity': 'switch_patch_port'}


class PhonePort(PatchPort):
    """A patch panel port that's connected to a third party"""
    id = Column(Integer, ForeignKey(PatchPort.id), primary_key=True,
                nullable=False)
    room = relationship(Room, backref=backref("phone_patch_ports"))

    __mapper_args__ = {'polymorphic_identity': 'phone_patch_port'}
