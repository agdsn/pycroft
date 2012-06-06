# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.properties
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by AG DSN.
"""
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy.orm import relationship, backref
from sqlalchemy.types import BigInteger, Integer, DateTime
from sqlalchemy.types import String


class Group(ModelBase):
    name = Column(String(255), nullable=False)
    discriminator = Column('type', String(17), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}


class Membership(ModelBase):
    start_date = Column(DateTime)
    end_date = Column(DateTime, nullable=True)

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                        nullable=False)
    #TODO prüfen, ob cascade Memberships löscht, wenn zugehörige Gruppe deleted
    group = relationship("Group", backref=backref("memberships",
                                                  cascade="all, delete",
                                                  order_by='Membership.id'))
    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True,
                        nullable=False)

    #TODO prüfen, ob cascade Memberships löscht, wenn zugehöriger User deleted
    user = relationship("User", backref=backref("memberships",
                                                cascade="all, delete",
                                                order_by='Membership.id'))


class Property(ModelBase):
    name = Column(String(255), nullable=False)

    # many to one from Property to PropertyGroup
    # nullable=True
    property_group_id = Column(Integer, ForeignKey("propertygroup.id"),
                            nullable=False)
    #TODO prüfen, ob cascade Properties löscht, wenn zugehörige PGroup deleted
    property_group = relationship("PropertyGroup",
        backref=backref("properties", cascade="all,delete"))

properties = {
    u"internet": u"Nutzer darf sich mit dem Internet verbinden",
    u"no_internet": u"Nutzer darf sich NICHT mit dem Internet verbinden",
    u"mail": u"Nutzer darf E-Mails versenden (und empfangen)",
    u"ssh_helios" : u"Nutzer darf sich mit SSH auf Helios einloggen",
    u"no_ssh_helios" : u"Nutzer darf sich NICHT mit SSH auf Helios einloggen",
    u"homepage_helios" : u"Nutzer darf eine Hompage auf Helios anlegen",
    u"no_pay" : u"Nutzer muss keinen Semesterbeitrag zahlen",
    u"show_user" : u"Nutzer darf andere Nutzer in der Usersuite sehen",
    u"change_mac" : u"Nutzer darf MAC Adressen ändern",
    u"change_user" : u"Nutzer darf Nutzer erstellen, ändern, löschen",
    u"finance" : u"Nutzer darf Finanzen einsehen und verwalten",
    u"root" : u"Nutzer darf Infrastruktur verwalten"
}

class PropertyGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'propertygroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                nullable=False)


class TrafficGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'trafficgroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                nullable=False)
    # in byte per seven days, zero is no limit
    traffic_limit = Column(BigInteger, nullable=False)
