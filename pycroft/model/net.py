# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.hosts
    ~~~~~~~~~~~~~~

    This module contains the classes Host, NetDevice, Switch.

    :copyright: (c) 2011 by AG DSN.
"""
import re
import ipaddr
from sqlalchemy import Column, Enum, ForeignKey, Table, event
from sqlalchemy.orm import backref, object_session, relationship, validates
from sqlalchemy.types import Integer, String
from pycroft.model.base import ModelBase
from pycroft.helpers.net import MacExistsException, mac_regex


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

    # one to one from Host to User
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


class InvalidMACAddressException(Exception):
    pass


class MulticastFlagException(InvalidMACAddressException):
    pass


class NetDevice(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    #mac = Column(postgresql.MACADDR, nullable=False)
    mac = Column(String(17), nullable=False)

    host_id = Column(Integer, ForeignKey(Host.id, ondelete="CASCADE"),
                     nullable=False)

    @validates('mac')
    def validate_mac(self, _, value):
        match = mac_regex.match(value)
        if not match:
            raise InvalidMACAddressException()
        components = match.groupdict()
        mac_bytes = (components['byte1'], components['byte2'],
                     components['byte3'], components['byte4'],
                     components['byte5'], components['byte6'])
        if int(mac_bytes[0], base=16) & 1:
            raise MulticastFlagException()
        return ':'.join(mac_bytes).lower()


class UserNetDevice(NetDevice):
    id = Column(Integer, ForeignKey(NetDevice.id, ondelete="CASCADE"),
                primary_key=True)

    __mapper_args__ = {'polymorphic_identity': "user_net_device"}

    host = relationship(UserHost,
                        backref=backref("user_net_device", uselist=False,
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


class Ip(ModelBase):
    def __init__(self, *args, **kwargs):
        super(Ip, self).__init__(*args, **kwargs)

        if self.address is not None and self.subnet is not None:
            assert self.is_ip_valid, "Subnet does not contain the ip"

    address = Column(String(51), unique=True, nullable=False)
    #address = Column(postgresql.INET, nullable=True)

    net_device_id = Column(Integer,
                           ForeignKey(NetDevice.id, ondelete="CASCADE"),
                           nullable=False)
    net_device = relationship(NetDevice,
                              backref=backref("ips",
                                              cascade="all, delete-orphan"))

    host = relationship(Host, secondary="net_device", backref=backref("ips"),
                        viewonly=True)

    subnet_id = Column(Integer, ForeignKey("subnet.id", ondelete="CASCADE"),
                       nullable=False)
    subnet = relationship("Subnet",
                          backref=backref("ips", cascade="all, delete-orphan"),
                          lazy='joined')

    def change_ip(self, ip, subnet):
        self.subnet = None
        self.address = ip
        self.subnet = subnet

    def _ip_subnet_valid(self, ip, subnet):
        return ipaddr.IPAddress(ip) in ipaddr.IPNetwork(subnet.address)

    @property
    def is_ip_valid(self):
        if self.address is None or self.subnet is None:
            return False
        return self._ip_subnet_valid(self.address, self.subnet)

    @validates('subnet')
    def validate_subnet(self, _, value):
        if value is None:
            return value
        if self.address is not None:
            assert self._ip_subnet_valid(self.address, value),\
                "Given subnet does not contain the ip"
        return value

    @validates("address")
    def validate_address(self, _, value):
        if value is None:
            return value
        if self.subnet is not None:
            assert self._ip_subnet_valid(value, self.subnet),\
                "Subnet does not contain the given ip"
        return value


def _check_correct_ip_subnet(mapper, connection, target):
    if target.address is not None and target.subnet is not None:
        assert target.is_ip_valid, "Subnet does not contain the ip"


event.listen(Ip, "before_insert", _check_correct_ip_subnet)
event.listen(Ip, "before_update", _check_correct_ip_subnet)


class VLAN(ModelBase):
    name = Column(String(127), nullable=False)
    tag = Column(Integer, nullable=False)


class Subnet(ModelBase):
    #address = Column(postgresql.INET, nullable=False)
    address = Column(String(51), nullable=False)
    #gateway = Column(postgresql.INET, nullable=False)
    gateway = Column(String(51), nullable=False)
    dns_domain = Column(String)
    reserved_addresses = Column(Integer, default=0, nullable=False)
    ip_type = Column(Enum("4", "6", name="subnet_ip_type"), nullable=False)

    # many to many from Subnet to VLAN
    vlans = relationship(VLAN, backref=backref("subnets"),
                         secondary=lambda: association_table_subnet_vlan)

    @property
    def netmask(self):
        net = ipaddr.IPNetwork(self.address)
        return str(net.netmask)

    @property
    def ip_version(self):
        return ipaddr.IPNetwork(self.address).version


association_table_subnet_vlan = Table(
    "association_subnet_vlan",
    ModelBase.metadata,
    Column("subnet_id", Integer, ForeignKey(Subnet.id)),
    Column("vlan_id", Integer, ForeignKey(VLAN.id)))


class Port(ModelBase):
    # Joined table inheritance
    discriminator = Column('type', String(15), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}

    name = Column(String(8), nullable=False)

    name_regex = re.compile("[A-Z][1-9][0-9]?")


class DestinationPort(Port):
    id = Column(Integer, ForeignKey(Port.id), primary_key=True,
                nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'destination_port'}


class PatchPort(Port):
    id = Column(Integer, ForeignKey(Port.id), primary_key=True,
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
    id = Column(Integer, ForeignKey(DestinationPort.id), primary_key=True,
                nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'phone_port'}


class SwitchPort(DestinationPort):
    # Joined table inheritance
    id = Column(Integer, ForeignKey(DestinationPort.id), primary_key=True,
                nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'switch_port'}

    # many to one from SwitchPort to Switch
    switch_id = Column(Integer, ForeignKey("switch.id"), nullable=False)
    switch = relationship("Switch", backref=backref("ports"))
