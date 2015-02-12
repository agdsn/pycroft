# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.ports
    ~~~~~~~~~~~~~~

    This module contains the classes
    DestinationPort, PatchPort, PhonePort, Switchport.

    :copyright: (c) 2011 by AG DSN.
"""
import re
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer, String
from pycroft.model.base import ModelBase


class Port(ModelBase):
    # Joined table inheritance
    discriminator = Column('type', String(15), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}

    name = Column(String(8), nullable=False)
    
    name_regex = re.compile("[A-Z][1-9][0-9]?")


class DestinationPort(Port):
    id = Column(Integer, ForeignKey('port.id'), primary_key=True,
                nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'destination_port'}


class PatchPort(Port):
    id = Column(Integer, ForeignKey('port.id'), primary_key=True,
                nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'patch_port'}

    # one to one from PatchPort to DestinationPort
    destination_port_id = Column(Integer, ForeignKey(DestinationPort.id),
                                 nullable=True)
    destination_port = relationship(DestinationPort,
                                    foreign_keys=[destination_port_id],
                                    backref=backref("patch_port",
                                                    uselist=False))

    # many to one from PatchPort to Room
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False)
    room = relationship("Room", backref=backref("patch_ports"))


class PhonePort(DestinationPort):
    # Joined table inheritance
    id = Column(Integer, ForeignKey('destination_port.id'), primary_key=True,
                nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'phone_port'}


class SwitchPort(DestinationPort):
    # Joined table inheritance
    id = Column(Integer, ForeignKey('destination_port.id'), primary_key=True,
                nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'switch_port'}

    # many to one from SwitchPort to Switch
    switch_id = Column(Integer, ForeignKey("switch.id"), nullable=False)
    switch = relationship("Switch", backref=backref("ports"))
