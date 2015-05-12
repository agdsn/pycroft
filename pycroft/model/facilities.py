# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.building
    ~~~~~~~~~~~~~~

    This module contains the classes Building, Room, Subnet, VLAN.

    :copyright: (c) 2011 by AG DSN.
"""

from sqlalchemy import Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import backref, relationship
from sqlalchemy.types import Boolean, Integer, String

from pycroft.model.base import ModelBase


class Building(ModelBase):
    number = Column(String(3), nullable=False)
    short_name = Column(String(8), unique=True, nullable=False)
    street = Column(String(20), nullable=False)

    __table_args__ = (UniqueConstraint("street", "number", name="address"),)


class Room(ModelBase):
    number = Column(String(36), nullable=False)
    level = Column(Integer, nullable=False)
    inhabitable = Column(Boolean, nullable=False)

    # many to one from Room to Building
    building_id = Column(Integer, ForeignKey(Building.id), nullable=False)
    building = relationship(Building, backref=backref("rooms"))

    def __str__(self):
        return "{} {} {}".format(self.building.short_name, self.level,
                                 self.number)

    def __unicode__(self):
        return u"{} {} {}".format(self.building.short_name, self.level,
                                  self.number)

