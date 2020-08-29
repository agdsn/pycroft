# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, event, UniqueConstraint
from sqlalchemy.orm import backref, relationship, validates, object_session
from sqlalchemy.schema import Table
from sqlalchemy.types import Integer, String
from pycroft.helpers.i18n import gettext
from pycroft.helpers.net import mac_regex

from pycroft.model.base import ModelBase, IntegerIdModel
from pycroft.model.facilities import Room
from pycroft.model.net import Subnet
from pycroft.model.user import User
from pycroft.model.types import (
    IPAddress, MACAddress, InvalidMACAddressException)


class Host(IntegerIdModel):
    name = Column(String, nullable=True)

    # many to one from Host to User
    owner_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                      nullable=True, index=True)
    owner = relationship(User, backref=backref("hosts",
                                               cascade="all, delete-orphan"))

    # many to one from Host to Room
    room = relationship(Room, backref=backref("hosts"))
    # We don't want to `ONDELETE CASCADE` because deleting a room
    # should not delete a host being there
    room_id = Column(Integer, ForeignKey(Room.id, ondelete="SET NULL"),
                     index=True)


class Switch(ModelBase):
    """A switch with a name and mgmt-ip

    A `Switch` is directly tied to a `Host` because instead of having an `id`
    column, the primary key is `host_id`, a foreign key on a `Host`.
    """
    host_id = Column(Integer, ForeignKey(Host.id), primary_key=True, index=True)
    host = relationship(Host, backref=backref("switch", uselist=False))

    management_ip = Column(IPAddress, nullable=False)


# TODO: properly remove this, do a separate commit
# and explain why it does not work (switches → owner=root w/o room)
def _check_user_host_in_user_room(mapper, connection, userhost):
    if userhost.room is not userhost.owner.room:
        raise Exception("UserHost can only be in user's room")

#event.listen(Host, "before_insert", _check_user_host_in_user_room)
#event.listen(Host, "before_update", _check_user_host_in_user_room)


class MulticastFlagException(InvalidMACAddressException):
    message = "Multicast bit set in MAC address"


class TypeMismatch(Exception):
    pass


class Interface(IntegerIdModel):
    """A logical network interface (hence the single MAC address).

    This means many net interfaces can be connected to the same switch port.

    It has to be bound to a `UserHost`, not another kind of host (like `Switch`)
    """
    name = Column(String, nullable=True)

    mac = Column(MACAddress, nullable=False, unique=True)

    host_id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                     nullable=False, index=True)

    @validates('mac')
    def validate_mac(self, _, mac_address):
        match = mac_regex.match(mac_address)
        if not match:
            raise InvalidMACAddressException("MAC address '"+mac_address+"' is not valid")
        if int(mac_address[0:2], base=16) & 1:
            raise MulticastFlagException("Multicast bit set in MAC address")
        return mac_address

    host = relationship(Host,
                        backref=backref("interfaces",
                                        cascade="all, delete-orphan"))


# See the `SwitchPort.default_vlans` relationship
switch_port_default_vlans = Table(
    'switch_port_default_vlans', ModelBase.metadata,
    Column('switch_port_id', Integer, ForeignKey('switch_port.id', ondelete='CASCADE'),
           index=True),
    Column('vlan_id', Integer, ForeignKey('vlan.id', ondelete='CASCADE'),
           index=True),
)


class SwitchPort(IntegerIdModel):
    switch_id = Column(Integer, ForeignKey(Switch.host_id, ondelete="CASCADE"),
                       nullable=False, index=True)
    switch = relationship(Switch,
                          backref=backref("ports",
                                        cascade="all, delete-orphan"))
    name = Column(String(64), nullable=False)
    #: These are the VLANs that should theoretically be available at
    #: this switch port.  It is only used to calculate the pool of IPs
    #: to choose from e.g. when adding a user or migrating a host, and
    #: does not influence any functionality beyond that.
    default_vlans = relationship('VLAN', secondary='switch_port_default_vlans',
                                 back_populates='switch_ports')

    def __str__(self):
        return "{} {}".format(self.switch.host.name, self.name)

    __table_args__ = (UniqueConstraint("name", "switch_id"),)


class IP(IntegerIdModel):
    address = Column(IPAddress, nullable=False, unique=True)
    interface_id = Column(Integer,
                          ForeignKey(Interface.id, ondelete="CASCADE"),
                          nullable=False)
    interface = relationship(Interface,
                             backref=backref("ips",
                                             cascade="all, delete-orphan"))

    host = relationship(Host, secondary=Interface.__table__, sync_backref=False,
                        backref=backref("ips", viewonly=True), viewonly=True)

    subnet_id = Column(Integer, ForeignKey(Subnet.id, ondelete="CASCADE"),
                       nullable=False, index=True)
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
