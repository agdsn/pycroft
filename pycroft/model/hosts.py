# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.hosts
    ~~~~~~~~~~~~~~

    This module contains the classes Host, NetDevice, Switch.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey, event
from sqlalchemy import Column
#from sqlalchemy.dialects import postgresql
from pycroft.model import dormitory
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import Integer
from sqlalchemy.types import String

import re

from pycroft.helpers import host_helper


class Host(ModelBase):
    hostname = Column(String(255), nullable=False)
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    # many to one from Host to User
    user = relationship("User", backref=backref("hosts"))
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True)

    # many to one from Host to Room
    room = relationship(dormitory.Room, backref=backref("hosts"))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=True)


class NetDevice(ModelBase):
    #ipv4 = Column(postgresql.INET, nullable=True)
    ipv4 = Column(String(15), unique=True, nullable=True)
    #ipv6 = Column(postgresql.INET, nullable=True)
    ipv6 = Column(String(51), unique=True, nullable=True)
    #mac = Column(postgresql.MACADDR, nullable=False)
    mac = Column(String(12), nullable=False)

    subnet_id = Column(Integer, ForeignKey("subnet.id"), nullable=True)
    subnet = relationship("Subnet", backref=backref("net_devices"))

    # one to one from PatchPort to NetDevice
    patch_port_id = Column(Integer, ForeignKey('patchport.id'), nullable=True)
    patch_port = relationship("PatchPort", backref=backref("net_device",
                                                          uselist=False))

    host_id = Column(Integer, ForeignKey("host.id"), nullable=False)
    host = relationship("Host", backref=backref("net_devices"))

    mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")


    @validates('mac')
    def validate_mac(self, _, value):
        if not NetDevice.mac_regex.match(value):
            raise Exception("invalid MAC address!")
        if int(value[1], base=16) & 1:
            raise Exception("Multicast-Flag (least significant bit im "
                            "ersten Byte gesetzt)!")
        return value

    def set_v4address(self, ipv4_address, subnet):
        assert host_helper.select_subnet_for_ip(ipv4_address, (subnet, )) \
                is not None, "Subnet does not contain the given ip"
        self.ipv4 = ipv4_address
        self.subnet = subnet


def _check_correct_netdev_subnet(mapper, connection, target):
    if target.ipv4 is not None:
        assert target.subnet is not None, \
                "NetDevice has an ip bot no Subnet assigned!"
        assert host_helper.select_subnet_for_ip(target.ipv4,
                    (target.subnet, )) is not None, \
                "Assigned Subnet does not contain the assigned ip"

    if target.subnet is not None:
        assert target.ipv4 is not None, "A Subnet is assigned but no ip was set"


event.listen(NetDevice, "before_insert", _check_correct_netdev_subnet)
event.listen(NetDevice, "before_update", _check_correct_netdev_subnet)


class Switch(Host):
    __mapper_args__ = {'polymorphic_identity': 'switch'}
    id = Column(Integer, ForeignKey('host.id'), primary_key=True)

    name = Column(String(127), nullable=False)

    #management_ip = Column(postgresql.INET, nullable=False)
    management_ip = Column(String(51), unique=True, nullable=False)
