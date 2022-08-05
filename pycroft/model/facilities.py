# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.facilities
~~~~~~~~~~~~~~~~~~~~~~~~
"""
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import backref, relationship
from sqlalchemy.types import Boolean, Integer, String

from pycroft.model import ddl
from pycroft.model.address import Address, address_remove_orphans
from pycroft.model.base import IntegerIdModel
from pycroft.model.finance import Account


class Site(IntegerIdModel):
    name = Column(String(), nullable=False)


class Building(IntegerIdModel):
    site_id = Column(Integer, ForeignKey(Site.id), nullable=False, index=True)
    site = relationship(Site, backref=backref("buildings", cascade_backrefs=False))
    number = Column(String(), nullable=False)
    short_name = Column(String(), unique=True, nullable=False)
    street = Column(String(), nullable=False)
    wifi_available = Column(Boolean(), nullable=False, default=False)

    fee_account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    fee_account = relationship(Account, backref=backref("building",
                                                        uselist=False,
                                                        cascade_backrefs=False))

    swdd_haus_id = Column(Integer, nullable=True)

    __table_args__ = (UniqueConstraint("street", "number", name="building_address"),)

    @property
    def street_and_number(self):
        return f"{self.street} {self.number}"


class Room(IntegerIdModel):
    number = Column(String(), nullable=False)
    level = Column(Integer, nullable=False)
    inhabitable = Column(Boolean, nullable=False)

    # many to one from Room to Building
    building_id = Column(
        Integer, ForeignKey(Building.id, onupdate='CASCADE'), nullable=False,
        index=True,
    )
    building = relationship(Building, backref=backref("rooms", order_by=(level, number),
                                                      cascade_backrefs=False))

    address_id = Column(Integer, ForeignKey(Address.id), index=True, nullable=False)
    address = relationship(Address, backref=backref("rooms", cascade_backrefs=False))

    swdd_vo_suchname = Column(String, nullable=True)

    connected_patch_ports = relationship(
        'PatchPort',
        primaryjoin='and_(PatchPort.room_id == Room.id, PatchPort.switch_port_id != None)',
        viewonly=True,
    )

    users_sharing_address = relationship(
        'User',
        primaryjoin='and_(User.room_id == Room.id, User.address_id == Room.address_id)',
        viewonly=True,
    )

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

    __table_args__ = (UniqueConstraint('swdd_vo_suchname'),)


manager = ddl.DDLManager()
manager.add_trigger(Room.__table__, ddl.Trigger(
    'room_address_cleanup_trigger',
    Room.__table__,
    ('UPDATE', 'DELETE'),
    f'{address_remove_orphans.name}()',
))
manager.register()
