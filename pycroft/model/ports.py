# -*- coding: utf-8 -*-
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


class DestinationPort(Port, ModelBase):
    pass


class PatchPort(Port, ModelBase):

    destinationport_id = Column(Integer, ForeignKey('destinationport.id'))
    destinationport = relationship("DestinationPort", backref=backref(
        "patchport", uselist=False))

    netdevice_id = Column(Integer, ForeignKey('netdevice.id'))
    netdevice = relationship("NetDevice", backref=backref("patchport",
                                                          uselist=False))


class PhonePort(DestinationPort, ModelBase):
    pass


class SwitchPort(DestinationPort, ModelBase):

    # many to one from SwitchPort to Switch
    switch_id = Column(Integer, ForeignKey("switch.id"))
    switch = relationship("Switch", backref=backref("ports"))
