# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship
from sqlalchemy.types import Boolean, Integer, String

from pycroft.model.address import Address
from pycroft.model.base import IntegerIdModel
from pycroft.model.finance import Account


class Site(IntegerIdModel):
    name = Column(String(), nullable=False)


class Building(IntegerIdModel):
    site_id = Column(Integer, ForeignKey(Site.id), nullable=False, index=True)
    site = relationship(Site, backref=backref("buildings"))
    number = Column(String(), nullable=False)
    short_name = Column(String(), unique=True, nullable=False)
    street = Column(String(), nullable=False)
    wifi_available = Column(Boolean(), nullable=False, default=False)

    fee_account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    fee_account = relationship(Account, backref=backref("building",
                                                        uselist=False))
    
    __table_args__ = (UniqueConstraint("street", "number", name="building_address"),)


class Room(IntegerIdModel):
    number = Column(String(), nullable=False)
    level = Column(Integer, nullable=False)
    inhabitable = Column(Boolean, nullable=False)

    # many to one from Room to Building
    building_id = Column(
        Integer, ForeignKey(Building.id, onupdate='CASCADE'), nullable=False,
        index=True,
    )
    building = relationship(Building, backref=backref("rooms", order_by=(level, number)))

    address_id = Column(Integer, ForeignKey(Address.id), index=True, nullable=False)
    address = relationship(Address, backref=backref("rooms"))

    connected_patch_ports = relationship(
        'PatchPort',
        primaryjoin='and_(PatchPort.room_id == Room.id, PatchPort.switch_port_id != None)',
    )

    def __str__(self):
        return "{} {} {}".format(self.building.short_name, self.level,
                                 self.number)

    def __unicode__(self):
        return u"{} {} {}".format(self.building.short_name, self.level,
                                  self.number)

    @hybrid_property
    def short_name(self):
        return "{} {}-{}".format(self.building.short_name, self.level, self.number)

    @hybrid_property
    def is_switch_room(self):
        from pycroft.model.host import Host
        from pycroft.model.host import Switch

        return Host.q.join(Switch, Host.id == Switch.host_id).filter(Host.room_id==self.id).first() is not None
