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
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey('group.id'),
                        nullable=False)
    #TODO prüfen, ob cascade Memberships löscht, wenn zugehörige Gruppe deleted
    group = relationship("Group", backref=backref("memberships",
                                                  cascade="all, delete",
                                                  order_by='Membership.id'))
    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey('user.id'),
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


class PropertyGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'propertygroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                nullable=False)

    def has_property(self, property_name):
        if Property.q.filter_by(property_group_id=self.id,
            name=property_name).count() > 0:
            return True

        return False


class TrafficGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'trafficgroup'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
                nullable=False)
    # in byte per seven days, zero is no limit
    traffic_limit = Column(BigInteger, nullable=False)


property_categories = [
    (u"Rechte Nutzer",
     [
         (u"internet", u"Nutzer darf sich mit dem Internet verbinden"),
         (u"mail", u"Nutzer darf E-Mails versenden (und empfangen)"),
         (u"ssh_helios", u"Nutzer darf sich mit SSH auf Helios einloggen"),
         (u"homepage_helios", u"Nutzer darf eine Hompage auf Helios anlegen"),
         (u"no_pay", u"Nutzer muss keinen Semesterbeitrag zahlen")
     ]
        ),
    (u"Verbote Nutzer",
     [
         (u"no_internet", u"Nutzer darf sich NICHT mit dem Internet verbinden"),
         (u"no_ssh_helios", u"Nutzer darf sich NICHT mit SSH auf Helios einloggen")
     ]
        ),
    (u"Nutzeradministration",
     [
         (u"user_show", u"Nutzer darf andere Nutzer in der Usersuite sehen"),
         (u"user_change", u"Nutzer darf Nutzer erstellen, ändern, löschen"),
         (u"mac_change", u"Nutzer darf MAC Adressen ändern")
     ]
        ),
    (u"Finanzadministration",
     [
         (u"finance_show", u"Nutzer darf Finanzen einsehen"),
         (u"finance_change", u"Nutzer darf Finanzen ändern")
     ]
        ),
    (u"Infrastrukturadministration",
     [
         (u"infrastructure_show", u"Nutzer darf Infrastruktur ansehen"),
         (u"infrastructure_change", u"Nutzer darf Infrastruktur verwalten")
     ]
        )
]


def get_properties():
    properties = []
    for category in property_categories:
        for property in category[1]:
            properties.append(property[0])

    return properties
