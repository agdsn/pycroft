# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.ports
    ~~~~~~~~~~~~~~

    This module contains the classes
    DestinationPort, PatchPort, PhonePort, Switchport.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer
from sqlalchemy.types import String


class Port(object):
    name = Column(String(4))


class DestinationPort(Port):
    pass

    # one to one from DestinationPort to PatchPort


class PatchPort(Port, ModelBase):
    pass


class PhonePort(DestinationPort, ModelBase):
    pass


class SwitchPort(DestinationPort, ModelBase):

    # many to one from SwitchPort to Switch
    switch_id = Column(Integer, ForeignKey("switch.id"))
    switch = relationship("Switch", backref=backref("ports"))
