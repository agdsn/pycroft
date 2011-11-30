# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.hosts
    ~~~~~~~~~~~~~~

    This module contains the classes Host, NetDevice, Switch.

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
#from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import Integer
from sqlalchemy.types import String


class Host(ModelBase):
    hostname = Column(String(255))

    # one to one from NetDevice to PatchPort

    # many to one from Host to User
    user = relationship("User", backref=backref("hosts"))
    user_id = Column(Integer, ForeignKey("user.id"))


class NetDevice(ModelBase):
    #ipv4 = Column(postgresql.INET);
    ipv4 = Column(String(12), unique=True)
    #ipv6 = Column(postgresql.INET);
    ipv6 = Column(String(51), unique=True)
    #mac = Column(postgresql.MACADDR)
    mac = Column(String(12))
    patch_port_id = Column(Integer, ForeignKey("patchport.id"))


class Switch(Host):
    # Concrete Table Inheritance
    __mapper_args__ = {"concrete": True}

    name = Column(String(127))
