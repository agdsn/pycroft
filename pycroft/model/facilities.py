# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.facilities
~~~~~~~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations
import operator
import typing as t

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column

from pycroft.model import ddl
from pycroft.model.address import Address, address_remove_orphans
from pycroft.model.base import IntegerIdModel
from .finance import Account

if t.TYPE_CHECKING:
    # backrefs:
    from .user import User, RoomHistoryEntry
    from .port import PatchPort
    from .logging import RoomLogEntry
    from .swdd import Tenancy


class Site(IntegerIdModel):
    name: Mapped[str]

    # backrefs
    buildings: Mapped[list[Building]] = relationship(back_populates="site")
    # /backrefs


class Building(IntegerIdModel):
    site_id: Mapped[int] = mapped_column(ForeignKey(Site.id), index=True)
    site: Mapped[Site] = relationship(back_populates="buildings")
    number: Mapped[str]
    short_name: Mapped[str] = mapped_column(unique=True)
    street: Mapped[str]
    wifi_available: Mapped[bool] = mapped_column(default=False)

    fee_account_id: Mapped[int] = mapped_column(ForeignKey(Account.id))
    fee_account: Mapped[Account] = relationship(back_populates="building")

    swdd_haus_id: Mapped[int | None]

    __table_args__ = (UniqueConstraint("street", "number", name="building_address"),)

    # backrefs
    rooms: Mapped[list[Room]] = relationship(
        back_populates="building", order_by="(Room.level, Room.number)"
    )
    # /backrefs

    @property
    def street_and_number(self):
        return f"{self.street} {self.number}"


class Room(IntegerIdModel):
    number: Mapped[str]
    level: Mapped[int]
    inhabitable: Mapped[bool]

    # many to one from Room to Building
    building_id: Mapped[int] = mapped_column(
        ForeignKey(Building.id, onupdate="CASCADE"),
        index=True,
    )
    building: Mapped[Building] = relationship(back_populates="rooms")

    address_id: Mapped[int] = mapped_column(ForeignKey(Address.id), index=True)
    address: Mapped[Address] = relationship(back_populates="rooms")

    swdd_vo_suchname: Mapped[str | None]

    connected_patch_ports: Mapped[list[PatchPort]] = relationship(
        primaryjoin='and_(PatchPort.room_id == Room.id, PatchPort.switch_port_id != None)',
        viewonly=True,
    )

    users_sharing_address: Mapped[list[User]] = relationship(
        primaryjoin='and_(User.room_id == Room.id, User.address_id == Room.address_id)',
        viewonly=True,
    )

    # backrefs
    users: Mapped[list[User]] = relationship(back_populates="room", viewonly=True)
    room_history_entries: Mapped[list[RoomHistoryEntry]] = relationship(
        back_populates="room",
        order_by="RoomHistoryEntry.id",
        viewonly=True
    )
    log_entries: Mapped[list[RoomLogEntry]] = relationship(
        back_populates="room", viewonly=True, cascade="all, delete-orphan"
    )
    patch_ports: Mapped[list[PatchPort]] = relationship(
        foreign_keys="PatchPort.room_id",
        back_populates="room",
        cascade="all, delete-orphan",
    )
    tenancies: Mapped[list[Tenancy]] = relationship(
        back_populates="room",
        viewonly=True,
    )
    # /backrefs

    def __str__(self):
        return self.short_name

    def __unicode__(self):
        return self.short_name

    @property
    def short_name(self):
        return f"{self.building.short_name} {self.level_and_number}"

    @property
    def level_and_number(self):
        return f"{self.level}-{self.number}"

    @property
    def is_switch_room(self):
        from pycroft.model.host import Host
        from pycroft.model.host import Switch

        return Host.q.join(Switch, Host.id == Switch.host_id).filter(Host.room_id==self.id).first() is not None

    @property
    def latest_log_entry(self) -> RoomLogEntry | None:
        if not (le := self.log_entries):
            return None
        return max(le, key=operator.attrgetter("created_at"))

    __table_args__ = (UniqueConstraint('swdd_vo_suchname'),)


manager = ddl.DDLManager()
manager.add_trigger(Room.__table__, ddl.Trigger(
    'room_address_cleanup_trigger',
    Room.__table__,
    ('UPDATE', 'DELETE'),
    f'{address_remove_orphans.name}()',
))
manager.register()
