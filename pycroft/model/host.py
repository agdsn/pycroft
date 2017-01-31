# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import CIDR
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import Integer, String

from pycroft.helpers.net import mac_regex
from pycroft.model.base import ModelBase
from pycroft.model.facilities import Room
from pycroft.model.types import (
    IPAddress, MACAddress, InvalidMACAddressException)
from pycroft.model.user import User


class HostReservation(ModelBase):
    id = Column(Integer, primary_key=True)

    name = Column(String(63))

    owner = relationship(User, backref=backref(
        "user_hosts", cascade="all, delete-orphan"))

    mac = Column(MACAddress, nullable=False)

    ip = Column(CIDR, nullable=False, unique=True)

    @validates('mac')
    def validate_mac(self, _, mac_address):
        match = mac_regex.match(mac_address)
        if not match:
            raise InvalidMACAddressException("MAC address '"+mac_address+"' is not valid")
        if int(mac_address[0:2], base=16) & 1:
            raise MulticastFlagException("Multicast bit set in MAC address")
        return mac_address


class NAS(ModelBase):
    id = Column(Integer, primary_key=True)

    name = Column(String(127), nullable=False)

    radius_key = Column(String(127), nullable=False)

    management_ip = Column(IPAddress, nullable=False)

    # many to one from NAS to Room
    room = relationship(Room, backref=backref("nas"))
    room_id = Column(Integer, ForeignKey(Room.id, ondelete="SET NULL"),
                     nullable=True)


class MulticastFlagException(InvalidMACAddressException):
    message = "Multicast bit set in MAC address"


class TypeMismatch(Exception):
    pass



class SwitchInterface(ModelBase):
    id = Column(Integer, primary_key=True)

    host = relationship(NAS,
                        backref=backref("switch_interfaces",
                                        cascade="all, delete-orphan"))

    name = Column(String(64), nullable=False)


    # many to one from SwitchInterface to Room
    destination_room = relationship(Room, backref=backref("switch_interfaces"))
    destination_room_id = Column(Integer, ForeignKey(Room.id, ondelete="SET NULL"),
                 nullable=True)
