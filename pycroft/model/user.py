# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.user
    ~~~~~~~~~~~~~~

    This module contains the class User.

    :copyright: (c) 2011 by AG DSN.
"""
import re

from flask.ext.login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_method
from sqlalchemy import (
    ForeignKey, Column, and_, DateTime, Integer,
    String, select, join, exists, null, not_)
from sqlalchemy.orm import backref, object_session, relationship, validates
from sqlalchemy.orm.util import has_identity
from sqlalchemy.sql import true, false

from pycroft.helpers.interval import (
    IntervalSet, UnboundedInterval, closed, single)
from pycroft.helpers.user import hash_password, verify_password
from pycroft.model import session
from pycroft.model.base import ModelBase
import pycroft.model.property
from pycroft.model.finance import FinanceAccount


class User(ModelBase, UserMixin):
    login = Column(String(40), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    registered_at = Column(DateTime, nullable=False)
    passwd_hash = Column(String)
    email = Column(String(255), nullable=True)

    # one to one from User to FinanceAccount
    finance_account = relationship("FinanceAccount",
                                   backref=backref("user", uselist=False))
    finance_account_id = Column(Integer, ForeignKey("finance_account.id"),
                                nullable=False)

    # many to one from User to Room
    room_id = Column(Integer, ForeignKey("room.id", ondelete="SET NULL"),
                     nullable=True)
    room = relationship("Room",
                        backref=backref("users", cascade="all"))

    traffic_groups = relationship("TrafficGroup",
                                  secondary=lambda: pycroft.model.property.Membership.__table__,
                                  viewonly=True)

    property_groups = relationship("PropertyGroup",
                                   secondary=lambda: pycroft.model.property.Membership.__table__,
                                   viewonly=True)

    login_regex = re.compile("^[a-z][a-z0-9_]{1,20}[a-z0-9]$")
    email_regex = re.compile(r"^[a-zA-Z0-9]+(?:(?:\+|-|_|\.)[a-zA-Z0-9]+)*"
                             r"@(?:[a-zA-Z0-9]+(?:\.|-))+[a-zA-Z]+$")

    blocked_logins = ["root", "daemon", "bin", "sys", "sync", "games", "man",
                      "lp", "mail", "news", "uucp", "proxy", "majordom",
                      "postgres", "wwwadmin", "backup", "msql", "operator",
                      "ftp", "ftpadmin", "guest", "bb", "nobody"]

    @validates('login')
    def validate_login(self, _, value):
        assert not has_identity(self), "user already in the database - cannot change login anymore!"
        if not User.login_regex.match(value) or value in self.blocked_logins:
            raise Exception("invalid unix-login!")
        return value

    @validates('email')
    def validate_email(self, _, value):
        assert User.email_regex.match(value)
        return value

    @validates('passwd_hash')
    def validate_passwd_hash(self, _, value):
        assert value is not None, "Cannot clear the password hash!"
        assert len(value) > 9, "A password-hash with les than 9 chars is not correct!"
        return value

    def check_password(self, plaintext_password):
        """verify a given plaintext password against the users passwd hash.

        """
        return verify_password(plaintext_password, self.passwd_hash)

    def set_password(self, plain_password):
        """Store a hash of a given plaintext passwd for the user.

        """
        self.passwd_hash = hash_password(plain_password)

    @staticmethod
    def verify_and_get(login, plaintext_password):
        user = User.q.filter_by(login=login).first()
        if user is not None and user.check_password(plaintext_password):
            return user
        return None

    @hybrid_method
    def active_memberships(self, when=None):
        if when is None:
            now = session.utcnow()
            when = single(now)
        return [m for m in self.memberships
                if when.overlaps(closed(m.begins_at, m.ends_at))]

    @active_memberships.expression
    def active_memberships(cls, when=None):
        return select([pycroft.model.property.Membership]).select_from(
            join(cls, pycroft.model.property.Membership)
        ).where(
            pycroft.model.property.Membership.active(when)
        )

    @hybrid_method
    def active_property_groups(self, when=None):
        return object_session(self).query(
            pycroft.model.property.PropertyGroup
        ).join(
            pycroft.model.property.Membership
        ).filter(
            pycroft.model.property.Membership.active(when),
            pycroft.model.property.Membership.user_id == self.id
        ).all()

    @active_property_groups.expression
    def active_property_groups(cls, when=None):
        return select([pycroft.model.property.PropertyGroup]).select_from(
            join(pycroft.model.property.PropertyGroup,
                 pycroft.model.property.Membership).join(cls)
        ).where(
            pycroft.model.property.Membership.active(when)
        )

    @hybrid_method
    def active_traffic_groups(self, when=None):
        return object_session(self).query(
            pycroft.model.property.TrafficGroup
        ).join(
            pycroft.model.property.Membership
        ).filter(
            pycroft.model.property.Membership.active(when),
            pycroft.model.property.Membership.user_id == self.id
        ).all()

    @active_traffic_groups.expression
    def active_traffic_groups(cls, when=None):
        return select([pycroft.model.property.TrafficGroup]).select_from(
            join(pycroft.model.property.TrafficGroup,
                 pycroft.model.property.Membership).join(cls)
        ).where(
            pycroft.model.property.Membership.active(when)
        )

    @hybrid_method
    def has_property(self, property_name, when=None):
        """
        :param str property_name: name of a property
        :param Interval when:
        """
        if when is None:
            now = session.utcnow()
            when = single(now)
        prop_granted_flags = [
            group.property_grants[property_name]
            for group in self.active_property_groups(when)
            if property_name in group.property_grants
        ]
        return all(prop_granted_flags) and any(prop_granted_flags)

    @has_property.expression
    def has_property(cls, prop, when=None):
        # TODO Use joins
        property_granted_select = select(
            [null()],
            from_obj=[
                pycroft.model.property.Property.__table__,
                pycroft.model.property.PropertyGroup.__table__,
                pycroft.model.property.Membership.__table__
            ]
        ).where(
            and_(
                pycroft.model.property.Property.name == prop,
                pycroft.model.property.Property.property_group_id == pycroft.model.property.PropertyGroup.id,
                pycroft.model.property.PropertyGroup.id == pycroft.model.property.Membership.group_id,
                pycroft.model.property.Membership.user_id == cls.id,
                pycroft.model.property.Membership.active(when)
            )
        )
        #.cte("property_granted_select")
        return and_(
            not_(exists(
                property_granted_select.where(
                    pycroft.model.property.Property.granted == false())

            )),
            exists(
                property_granted_select.where(
                    pycroft.model.property.Property.granted == true()
                )
            )
        ).label("has_property_" + prop)

    def property_intervals(self, name, when=UnboundedInterval):
        """
        Get the set of intervals in which the user was granted a given property
        :param str name:
        :param Interval when:
        :returns: The set of intervals in which the user was granted the
        property
        :rtype: IntervalSet
        """
        property_assignments = object_session(self).query(
            pycroft.model.property.Property.granted,
            pycroft.model.property.Membership.begins_at,
            pycroft.model.property.Membership.ends_at
        ).filter(
            pycroft.model.property.Property.name == name,
            pycroft.model.property.Property.property_group_id == pycroft.model.property.PropertyGroup.id,
            pycroft.model.property.PropertyGroup.id == pycroft.model.property.Membership.group_id,
            pycroft.model.property.Membership.user_id == self.id
        ).all()
        granted_intervals = IntervalSet(
            closed(begins_at, ends_at)
            for granted, begins_at, ends_at in property_assignments
            if granted
        )
        denied_intervals = IntervalSet(
            closed(begins_at, ends_at)
            for granted, begins_at, ends_at in property_assignments
            if not granted
        )
        return (granted_intervals - denied_intervals).intersect(when)
