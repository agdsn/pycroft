# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.properties
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by AG DSN.
"""
from datetime import datetime
from collections import OrderedDict

from sqlalchemy import (
    CheckConstraint, Column, ForeignKey, and_, or_, select, literal, null)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.session import object_session
from sqlalchemy.types import BigInteger, Boolean, DateTime, Integer, String

from pycroft.helpers.interval import closed, single
from pycroft.model import session, functions
from pycroft.model.base import ModelBase
import pycroft.model.user


class Group(ModelBase):
    name = Column(String(255), nullable=False)
    discriminator = Column('type', String(17), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}

    users = relationship(
        "User",
        secondary=lambda: Membership.__table__,
        viewonly=True
    )

    @hybrid_method
    def active_users(self, when=None):
        """
        :param Interval when:
        :rtype: list[User]
        """
        return object_session(self).query(pycroft.model.user.User).join(
            (Membership, Membership.user_id == pycroft.model.user.User.id),
        ).filter(
            Membership.active(when),
            Membership.group_id == self.id
        ).all()

    @active_users.expression
    def active_users(self, when=None):
        return select([pycroft.model.user.User]).join(
            (Membership, Membership.user_id == pycroft.model.user.User.id),
        ).where(
            Membership.active(when),
            Membership.group_id == self.id
        )


class Membership(ModelBase):
    start_date = Column(DateTime, nullable=True, default=functions.utcnow())
    end_date = Column(DateTime, nullable=True)

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey('group.id', ondelete="CASCADE"),
        nullable=False)
    group = relationship("Group", backref=backref("memberships",
        cascade="all, delete-orphan",
        order_by='Membership.id'))

    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"),
        nullable=False)
    user = relationship("User", backref=backref("memberships",
        cascade="all, delete-orphan",
        order_by='Membership.id'))

    __table_args = (
        CheckConstraint("start_date IS NULL OR "
                        "end_date OR IS NULL OR "
                        "start_date <= end_date")
    )

    @hybrid_method
    def active(self, when=None):
        if when is None:
            now = object_session(self).query(functions.utcnow()).scalar()
            when = single(now)

        return when.overlaps(closed(self.start_date, self.end_date))

    @active.expression
    def active(self, when=None):
        if when is None:
            now = session.utcnow()
            when = closed(now, now)

        return and_(
            or_(self.start_date == null(), literal(when.end) == null(),
                self.start_date <= literal(when.end)),
            or_(literal(when.begin) == null(), self.end_date == null(),
                literal(when.begin) <= self.end_date)
        ).label("active")

    @validates('end_date')
    def validate_end_date(self, _, value):
        if value is None:
            return value
        assert isinstance(value, datetime), \
            "end_date must be an instanceof  datetime"
        if self.start_date is not None:
            assert value >= self.start_date,\
                "start date must be before end date"
        return value

    @validates('start_date')
    def validate_start_date(self, _, value):
        if value is None:
            return value
        assert isinstance(value, datetime), "start_date should be a datetime"
        if self.end_date is not None:
            assert value <= self.end_date,\
                "start date must be before end date"
        return value

    def disable(self):
        now = session.utcnow()
        if self.start_date > now:
            self.end_date = self.start_date
        else:
            self.end_date = now


class Property(ModelBase):
    name = Column(String(255), nullable=False)
    granted = Column(Boolean, nullable=False)

    # many to one from Property to PropertyGroup
    # nullable=True
    property_group_id = Column(Integer, ForeignKey("property_group.id"),
        nullable=False)
    #TODO prüfen, ob cascade Properties löscht, wenn zugehörige PGroup deleted
    property_group = relationship(
        "PropertyGroup",
        backref=backref("properties", cascade="all, delete-orphan",
                        collection_class=attribute_mapped_collection("name"))
    )


class PropertyGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'property_group'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
        nullable=False)
    property_grants = association_proxy(
        "properties", "granted",
        creator=lambda k, v: Property(name=k, granted=v)
    )


class TrafficGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'traffic_group'}
    id = Column(Integer, ForeignKey('group.id'), primary_key=True,
        nullable=False)
    # in byte per seven days, zero is no limit
    traffic_limit = Column(BigInteger, nullable=False)


property_categories = OrderedDict((
    (u"Mitgliedstatus", OrderedDict((
        (u"member", u"Mitglied"),
        (u"active_member", u"aktives Mitglied"),
        (u"former_active_member", u"ehemals aktives Mitglied"),
        (u"advisory_member", u"beratendes Mitglied"),
        (u"honorary_member", u"Ehrenmitglied"),
        (u"away", u"vorübergehend ausgezogen"),
    ))),
    (u"Nutzerrechte", OrderedDict((
        (u"network_access",  u"besitzt Zugang zum Studentennetz"),
        (u"negative_balance",  u"darf negative Kontobilanz haben"),
        (u"registration_fee_exemption",  u"von Anmeldegebühr befreit"),
        (u"semester_contribution_exemption",  u"von Semesterbeitrag befreit"),
        (u"overdue_fine_exemption",  u"von Versäumnisgebühr befreit"),
        (u"pay_registration_fee", u"Nutzer muss Anmeldegebühr zahlen"),
        (u"pay_semester_fee", u"Nutzer muss Semesterbeitrag zahlen"),
    ))),
    (u"Nutzerverwaltung", OrderedDict((
        (u"user_show",  u"darf Nutzerdaten einsehen"),
        (u"user_change",  u"darf Nutzer anlegen, ändern, löschen"),
        (u"user_mac_change",  u"darf MAC-Adressen ändern"),
    ))),
    (u"Finanzen", OrderedDict((
        (u"finance_show",  u"darf Finanzendaten einsehen"),
        (u"finance_change",  u"darf Finanzendaten ändern"),
    ))),
    (u"Infrastruktur", OrderedDict((
        (u"infrastructure_show",  u"darf Infrastruktur ansehen"),
        (u"infrastructure_change",  u"darf Infrastruktur anlegen, bearbeiten, löschen"),
        (u"dormitories_show",  u"darf Wohnheime einsehen"),
        (u"dormitories_change",  u"darf Wohnheime anlegen, bearbeiten, löschen"),
    ))),
    (u"Gruppenverwaltung", OrderedDict((
        (u"groups_show",  u"darf Gruppen einsehen"),
        (u"groups_change_membership",  u"darf Gruppenmitgliedschaften bearbeiten"),
        (u"groups_change",  u"darf Gruppen anlegen, bearbeiten, löschen"),
        (u"groups_traffic_show",  u"darf Trafficgruppen sehen"),
        (u"groups_traffic_change",  u"darf Trafficgruppen bearbeiten"),
    ))),
))
