# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, event
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import Integer, String
from pycroft.helpers.i18n import gettext
from pycroft.helpers.net import mac_regex

from pycroft.model.base import ModelBase
from pycroft.model.types import (
    IPAddress, MACAddress, InvalidMACAddressException)


class Host(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    # many to one from Host to User
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"),
                     nullable=True)

    # many to one from Host to Room
    room = relationship("Room", backref=backref("hosts"))
    room_id = Column(Integer, ForeignKey("room.id", ondelete="SET NULL"),
                     nullable=True)


class UserHost(Host):
    id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'user_host'}

    desired_name = Column(String(63))
    user = relationship("User", backref=backref(
        "user_hosts", cascade="all, delete-orphan"))


class ServerHost(Host):
    id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                primary_key=True)
    __mapper_args__ = {'polymorphic_identity': 'server_host'}

    name = Column(String(255))

    user = relationship("User", backref=backref(
        "server_hosts", cascade="all, delete-orphan"))


class Switch(Host):
    __mapper_args__ = {'polymorphic_identity': 'switch'}
    id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                primary_key=True)

    name = Column(String(127), nullable=False)

    management_ip = Column(String(127), nullable=False)

    user = relationship("User", backref=backref(
        "switches", cascade="all, delete-orphan"))


class MulticastFlagException(InvalidMACAddressException):
    pass


class NetDevice(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    mac = Column(MACAddress, nullable=False)

    host_id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                     nullable=False)

    @validates('mac')
    def validate_mac(self, _, value):
        match = mac_regex.match(value)
        if not match:
            raise InvalidMACAddressException()
        if int(value[0:2], base=16) & 1:
            raise MulticastFlagException()
        return value


class UserNetDevice(NetDevice):
    id = Column(Integer, ForeignKey(NetDevice.id, ondelete="CASCADE"),
                primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "user_net_device"}

    host = relationship(UserHost,
                        backref=backref("user_net_devices",
                                        cascade="all, delete-orphan"))


class ServerNetDevice(NetDevice):
    id = Column(Integer, ForeignKey(NetDevice.id, ondelete="CASCADE"),
                primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "server_net_device"}

    host = relationship(ServerHost,
                        backref=backref("server_net_devices",
                                        cascade="all, delete-orphan"))

    #TODO switch_port_id nicht Nullable machen: CLash mit Importscript
    switch_port_id = Column(Integer, ForeignKey('switch_port.id'),
                            nullable=True)
    switch_port = relationship("SwitchPort")


class SwitchNetDevice(NetDevice):
    id = Column(Integer, ForeignKey(NetDevice.id, ondelete="CASCADE"),
                primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "switch_net_device"}

    host = relationship("Switch",
                        backref=backref("switch_net_devices",
                                        cascade="all, delete-orphan"))


class IP(ModelBase):
    address = Column(IPAddress, nullable=False, unique=True)
    net_device_id = Column(Integer,
                           ForeignKey(NetDevice.id, ondelete="CASCADE"),
                           nullable=False)
    net_device = relationship(NetDevice,
                              backref=backref("ips",
                                              cascade="all, delete-orphan"))

    host = relationship(Host, secondary=NetDevice.__table__,
                        backref=backref("ips", viewonly=True), viewonly=True)

    subnet_id = Column(Integer, ForeignKey("subnet.id", ondelete="CASCADE"),
                       nullable=False)
    subnet = relationship("Subnet",
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
