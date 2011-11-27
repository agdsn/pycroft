# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.rights
    ~~~~~~~~~~~~~~

    This module contains the classes Group, Membership, Right.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Table, Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer, DateTime
from sqlalchemy.types import String


class Group(ModelBase):
    name = Column(String(255))


class Membership(ModelBase):
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    user = relationship("User", backref=backref("memberships", order_by=id))
    group = relationship("Group", backref=backref("memberships", order_by=id))


class Right(ModelBase):
    name = Column(String(255))
