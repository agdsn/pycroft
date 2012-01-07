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

from pycroft.model.hosts import Switch

class Port(object):
    name = Column(String(4))


class DestinationPort(Port, ModelBase):
    # Joined table inheritance
    discriminator = Column('type', String(15))
    __mapper_args__ = {'polymorphic_on': discriminator}


class PatchPort(Port, ModelBase):

    # one to one from PatchPort to DestinationPort
    destination_port_id = Column(Integer, ForeignKey('destinationport.id'))
    destination_port = relationship("DestinationPort", backref=backref(
                                    "patch_port", uselist=False))


class PhonePort(DestinationPort):
    # Joined table inheritance
    id = Column(Integer, ForeignKey('destinationport.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'phone_port'}


class SwitchPort(DestinationPort):
    # Joined table inheritance
    id = Column(Integer, ForeignKey('destinationport.id'), primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'switch_port'}

    # many to one from SwitchPort to Switch
    switch_id = Column(Integer, ForeignKey("switch.id"))
    switch = relationship(Switch, backref=backref("ports"))
