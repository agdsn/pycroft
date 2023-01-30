# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.host
~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations
import typing as t

import ipaddr
from sqlalchemy import ForeignKey, event, UniqueConstraint, Column
from sqlalchemy.orm import backref, relationship, validates, Mapped, mapped_column
from sqlalchemy.schema import Table
from sqlalchemy.types import Integer, String

from pycroft.helpers.i18n import gettext
from pycroft.helpers.net import mac_regex
from pycroft.model.base import ModelBase, IntegerIdModel
from pycroft.model.exc import PycroftModelException
from pycroft.model.facilities import Room
from pycroft.model.net import Subnet
from pycroft.model.type_aliases import mac_address
from pycroft.model.types import InvalidMACAddressException
from pycroft.model.user import User


if t.TYPE_CHECKING:
    # backref imports
    from .net import VLAN
    from .port import PatchPort


class Host(IntegerIdModel):
    name: Mapped[str | None]

    # many to one from Host to User
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), index=True
    )
    owner: Mapped[User] = relationship(User, back_populates="hosts")

    # We don't want to `ONDELETE CASCADE` because deleting a room
    # should not delete a host being there
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey(Room.id, ondelete="SET NULL"),
        index=True,
    )
    # many to one from Host to Room
    room: Mapped[Room | None] = relationship(
        Room, backref=backref("hosts", cascade_backrefs=False)
    )

    # backrefs
    interfaces: Mapped[list[Interface]] = relationship(
        back_populates="host",
        cascade="all, delete-orphan",
    )
    ips: Mapped[list[IP]] = relationship(
        secondary="interface", back_populates="host", viewonly=True
    )
    switch: Mapped[Switch | None] = relationship(
        back_populates="host", uselist=False, viewonly=True
    )
    # /backrefs


class Switch(ModelBase):
    """A switch with a name and mgmt-ip

    A `Switch` is directly tied to a `Host` because instead of having an `id`
    column, the primary key is `host_id`, a foreign key on a `Host`.
    """

    host_id: Mapped[int] = mapped_column(
        ForeignKey(Host.id), primary_key=True, index=True
    )
    host: Mapped[Host] = relationship(back_populates="switch")
    management_ip: Mapped[ipaddr._BaseIP]

    # backrefs
    ports: Mapped[list[SwitchPort]] = relationship(
        back_populates="switch",
        cascade="all, delete-orphan",
    )
    # /backrefs


# TODO: properly remove this, do a separate commit
# and explain why it does not work (switches → owner=root w/o room)
def _check_user_host_in_user_room(mapper, connection, userhost):
    if userhost.room is not userhost.owner.room:
        raise PycroftModelException("UserHost can only be in user's room")

#event.listen(Host, "before_insert", _check_user_host_in_user_room)
#event.listen(Host, "before_update", _check_user_host_in_user_room)


class MulticastFlagException(InvalidMACAddressException):
    message = "Multicast bit set in MAC address"


class TypeMismatch(PycroftModelException):
    pass


class Interface(IntegerIdModel):
    """A logical network interface (hence the single MAC address).

    This means many net interfaces can be connected to the same switch port.

    It has to be bound to a `UserHost`, not another kind of host (like `Switch`)
    """

    name: Mapped[str] = mapped_column(String, nullable=True)
    mac: Mapped[mac_address] = mapped_column(unique=True)

    host_id: Mapped[int] = mapped_column(
        ForeignKey(Host.id, ondelete="CASCADE"), index=True
    )
    host: Mapped[Host] = relationship(back_populates="interfaces")

    # backrefs
    ips: Mapped[list[IP]] = relationship(
        back_populates="interface", cascade="all, delete-orphan"
    )
    # /backrefs

    @validates('mac')
    def validate_mac(self, _, mac_address):
        match = mac_regex.match(mac_address)
        if not match:
            raise InvalidMACAddressException("MAC address '"+mac_address+"' is not valid")
        if int(mac_address[0:2], base=16) & 1:
            raise MulticastFlagException("Multicast bit set in MAC address")
        return mac_address


# See the `SwitchPort.default_vlans` relationship
switch_port_default_vlans = Table(
    'switch_port_default_vlans', ModelBase.metadata,
    Column('switch_port_id', Integer, ForeignKey('switch_port.id', ondelete='CASCADE'),
           index=True),
    Column('vlan_id', Integer, ForeignKey('vlan.id', ondelete='CASCADE'),
           index=True),
)


class SwitchPort(IntegerIdModel):
    switch_id: Mapped[int] = mapped_column(
        ForeignKey(Switch.host_id, ondelete="CASCADE"),
        index=True,
    )
    switch: Mapped[Switch] = relationship(Switch, back_populates="ports")
    name: Mapped[str] = mapped_column(String(64))

    #: These are the VLANs that should theoretically be available at
    #: this switch port.  It is only used to calculate the pool of IPs
    #: to choose from e.g. when adding a user or migrating a host, and
    #: does not influence any functionality beyond that.
    default_vlans: Mapped[list[VLAN]] = relationship(
        secondary="switch_port_default_vlans",
        back_populates="switch_ports",
    )

    # backrefs
    patch_port: Mapped[PatchPort | None] = relationship(
        back_populates="switch_port", uselist=False
    )
    # /backrefs

    def __str__(self):
        return f"{self.switch.host.name} {self.name}"

    __table_args__ = (UniqueConstraint("name", "switch_id"),)


class IP(IntegerIdModel):
    address: Mapped[ipaddr._BaseIP] = mapped_column(unique=True)
    interface_id: Mapped[int] = mapped_column(
        ForeignKey(Interface.id, ondelete="CASCADE")
    )
    interface: Mapped[Interface] = relationship(back_populates="ips")

    subnet_id: Mapped[int] = mapped_column(
        ForeignKey(Subnet.id, ondelete="CASCADE"), index=True
    )
    subnet: Mapped[Subnet] = relationship(Subnet, back_populates="ips", lazy="joined")

    # associations
    host: Mapped[Host] = relationship(
        secondary=Interface.__table__,
        back_populates="ips",
        viewonly=True,
    )
    # /associations

    def _check_subnet_valid(self, address, subnet):
        if address is None or subnet is None:
            return
        if address not in subnet:
            message = (
                gettext("IP address {} is not contained in its subnet {}")
                .format(address, subnet)
            )
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
