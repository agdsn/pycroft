# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, event
from sqlalchemy.orm import backref, relationship, validates, object_session
from sqlalchemy.schema import Table
from sqlalchemy.types import Integer, String
from pycroft.helpers.i18n import gettext
from pycroft.helpers.net import mac_regex
from pycroft.lib.net import MacExistsException

from pycroft.model.base import ModelBase
from pycroft.model.facilities import Room
from pycroft.model.net import Subnet
from pycroft.model.user import User
from pycroft.model.types import (
    IPAddress, MACAddress, InvalidMACAddressException)


class Host(ModelBase):
    discriminator = Column('type', String(50), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}

    # many to one from Host to User
    owner_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                      nullable=True)

    # many to one from Host to Room
    room = relationship(Room, backref=backref("hosts"))
    # We don't want to `ONDELETE CASCADE` because deleting a room
    # should not delete e.g. a switch assigned there
    room_id = Column(Integer, ForeignKey(Room.id))


class UserHost(Host):
    id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'user_host'}

    owner = relationship(User, backref=backref(
        "user_hosts", cascade="all, delete-orphan"))


class Switch(Host):
    __mapper_args__ = {'polymorphic_identity': 'switch'}
    id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                primary_key=True)

    name = Column(String(127), nullable=False)

    management_ip = Column(IPAddress, nullable=False)

    owner = relationship(User, backref=backref(
        "switches", cascade="all, delete-orphan"))


def _check_user_host_in_user_room(mapper, connection, userhost):
    if userhost.room is not userhost.owner.room:
        raise Exception("UserHost can only be in user's room")

event.listen(UserHost, "before_insert", _check_user_host_in_user_room)
event.listen(UserHost, "before_update", _check_user_host_in_user_room)


class MulticastFlagException(InvalidMACAddressException):
    message = "Multicast bit set in MAC address"


class TypeMismatch(Exception):
    pass


class Interface(ModelBase):
    """A logical network interface (hence the single MAC address), which means
    many net interfaces can be connected to the same switch port"""

    #foreign key discriminator
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    mac = Column(MACAddress, nullable=False)

    host_id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                     nullable=False)

    @validates('mac')
    def validate_mac(self, _, mac_address):
        match = mac_regex.match(mac_address)
        if not match:
            raise InvalidMACAddressException("MAC address '"+mac_address+"' is not valid")
        if int(mac_address[0:2], base=16) & 1:
            raise MulticastFlagException("Multicast bit set in MAC address")
        return mac_address


class UserInterface(Interface):
    id = Column(Integer, ForeignKey(Interface.id, ondelete="CASCADE"),
                primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "user_interface"}

    host = relationship(UserHost,
                        backref=backref("user_interfaces",
                                        cascade="all, delete-orphan"))


switch_port_association_table = Table(
    'switch_port_association', ModelBase.metadata,
    Column('switch_port_id', Integer, ForeignKey('switch_port.id', ondelete='CASCADE')),
    Column('subnet_id', Integer, ForeignKey('subnet.id', ondelete='CASCADE')),
)


class SwitchPort(ModelBase):
    host_id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                     nullable=False)
    host = relationship(Switch,
                        backref=backref("switch_ports",
                                        cascade="all, delete-orphan"))
    name = Column(String(64), nullable=False)
    subnets = relationship('Subnet', secondary='switch_port_association',
                           back_populates='switch_ports')

    def __str__(self):
        return "{} {}".format(self.host.name, self.name)


class IP(ModelBase):
    address = Column(IPAddress, nullable=False, unique=True)
    interface_id = Column(Integer,
                          ForeignKey(Interface.id, ondelete="CASCADE"),
                          nullable=False)
    interface = relationship(Interface,
                             backref=backref("ips",
                                             cascade="all, delete-orphan"))

    host = relationship(Host, secondary=Interface.__table__,
                        backref=backref("ips", viewonly=True), viewonly=True)

    subnet_id = Column(Integer, ForeignKey(Subnet.id, ondelete="CASCADE"),
                       nullable=False)
    subnet = relationship(Subnet,
                          backref=backref("ips", cascade="all, delete-orphan"),
                          lazy='joined')

    def _check_subnet_valid(self, address, subnet):
        if address is None or subnet is None:
            return
        if address not in subnet:
            message = gettext('IP address {} is not contained in its subnet {}'
                              .format(address, subnet))
            raise ValueError(message)

    @validates('subnet')
    def validate_subnet(self, _, value):
        if value is None:
            return value
        self._check_subnet_valid(self.address, value.address)
        return value

    @validates("address")
    def validate_address(self, _, value):
        if value is None or self.subnet is None:
            return value
        self._check_subnet_valid(value, self.subnet.address)
        return value


def _check_correct_ip_subnet(mapper, connection, target):
    if target.subnet is not None:
        target._check_subnet_valid(target.address, target.subnet.address)


event.listen(IP, "before_insert", _check_correct_ip_subnet)
event.listen(IP, "before_update", _check_correct_ip_subnet)
