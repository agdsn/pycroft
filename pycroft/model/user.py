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
from datetime import datetime
import re

from flask_login import UserMixin
from sqlalchemy import (
    Boolean, BigInteger, CheckConstraint, Column, DateTime, ForeignKey, Integer,
    String, and_, exists, join, literal, not_, null, or_, select, Sequence,
    Interval, Date)
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import backref, object_session, relationship, validates
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.util import has_identity
from sqlalchemy.sql import true, false

from pycroft.helpers.interval import (
    IntervalSet, UnboundedInterval, closed, single)
from pycroft.helpers.user import hash_password, verify_password
from pycroft.model import session, functions
from pycroft.model.base import ModelBase, IntegerIdModel


class IllegalLoginError(ValueError):
    pass


class IllegalEmailError(ValueError):
    pass


class User(IntegerIdModel, UserMixin):
    login = Column(String(40), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    registered_at = Column(DateTime, nullable=False)
    passwd_hash = Column(String)
    email = Column(String(255), nullable=True)
    birthdate = Column(Date, nullable=True)

    # one to one from User to Account
    account = relationship("Account", backref=backref("user", uselist=False))
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False)

    unix_account = relationship('UnixAccount')  # backref not really needed.
    unix_account_id = Column(Integer, ForeignKey('unix_account.id'),
                             nullable=True, unique=True)

    # many to one from User to Room
    room_id = Column(Integer, ForeignKey("room.id", ondelete="SET NULL"),
                     nullable=True)
    room = relationship("Room",
                        backref=backref("users", cascade="all"))

    traffic_groups = relationship("TrafficGroup",
                                  secondary=lambda: Membership.__table__,
                                  viewonly=True)

    property_groups = relationship("PropertyGroup",
                                   secondary=lambda: Membership.__table__,
                                   viewonly=True)

    _current_traffic_balance = relationship(
        'CurrentTrafficBalance',
        primaryjoin='User.id == foreign(CurrentTrafficBalance.user_id)',
        viewonly=True, uselist=False
    )

    @property
    def current_credit(self):
        return self._current_traffic_balance.amount

    #: This is a relationship to the `current_property` view filtering out
    #: the entries with `denied=True`.
    current_properties = relationship(
        'CurrentProperty',
        primaryjoin='and_(User.id == foreign(CurrentProperty.user_id),'
                    '~CurrentProperty.denied)',
        viewonly=True
    )
    #: This is a relationship to the `current_property` view ignoring the
    #: `denied` attribute.
    current_properties_maybe_denied = relationship(
        'CurrentProperty',
        primaryjoin='User.id == foreign(CurrentProperty.user_id)',
        viewonly=True
    )

    login_regex = re.compile(r"""
        ^
        # Must begin with a lowercase character
        [a-z]
        # Can continue with lowercase characters, numbers and some punctuation
        # but between punctuation characters must be characters or numbers
        (?:[._-]?[a-z0-9])+$
        """, re.VERBOSE)
    email_regex = re.compile(r"^[a-zA-Z0-9!#$%&'*+\-/=?^_`{|}~]+"
                             r"(?:\.[a-zA-Z0-9!#$%&'*+\-/=?^_`{|}~]+)*"
                             r"@(?:[a-zA-Z0-9]+(?:\.|-))+[a-zA-Z]+$")

    blocked_logins = {"abuse", "admin", "administrator", "autoconfig",
                      "broadcasthost", "root", "daemon", "bin", "sys", "sync",
                      "games", "man", "hostmaster", "imap", "info", "is",
                      "isatap", "it", "localdomain", "localhost",
                      "lp", "mail", "mailer-daemon", "news", "uucp", "proxy",
                      # ground control to
                      "majordom", "marketing", "mis", "noc", "website", "api"
                      "noreply", "no-reply", "pop", "pop3", "postmaster",
                      "postgres", "sales", "smtp", "ssladmin", "status",
                      "ssladministrator", "sslwebmaster", "support",
                      "sysadmin", "usenet", "webmaster", "wpad", "www",
                      "wwwadmin", "backup", "msql", "operator", "user",
                      "ftp", "ftpadmin", "guest", "bb", "nobody", "www-data",
                      "bacula", "contact", "email", "privacy", "anonymous",
                      "web", "git", "username", "log", "login", "help", "name"}

    login_character_limit = 22

    def __init__(self, **kwargs):
        password = kwargs.pop('password', None)
        super(User, self).__init__(**kwargs)
        if password is not None:
            self.password = password

    @validates('login')
    def validate_login(self, _, value):
        assert not has_identity(self), "user already in the database - cannot change login anymore!"
        if not self.login_regex.match(value):
            raise IllegalLoginError(
                "Illegal login '{}': Logins must begin with a lower case "
                "letter and may be followed by lower case letters, digits or "
                "punctuation (dash, underscore and dot). Punctuation "
                "characters must be separated by at least on letter or digit."
                .format(value)
            )
        if value in self.blocked_logins:
            raise IllegalLoginError(
                "Illegal login '{}': This login is blocked and may not be used."
                .format(value)
            )
        if len(value) > self.login_character_limit:
            raise IllegalLoginError(
                "Illegal login '{}': Logins are limited to at most {} "
                "characters.".format(value, self.login_character_limit)
            )
        return value

    @validates('email')
    def validate_email(self, _, value):
        if not value:
            return value
        if not self.email_regex.match(value):
            raise IllegalEmailError("Illegal email '{}'".format(value))
        return value

    @validates('passwd_hash')
    def validate_passwd_hash(self, _, value):
        assert value is not None, "Cannot clear the password hash!"
        assert len(value) > 9, "A password-hash with less than 9 chars is " \
                               "not correct!"
        return value

    def check_password(self, plaintext_password):
        """verify a given plaintext password against the users passwd hash.

        """
        return verify_password(plaintext_password, self.passwd_hash)

    @hybrid_property
    def password(self):
        """Store a hash of a given plaintext passwd for the user.

        """
        raise RuntimeError("Password can not be read, only set")

    @password.setter
    def password(self, value):
        self.passwd_hash = hash_password(value)

    @staticmethod
    def verify_and_get(login, plaintext_password):
        try:
            user = User.q.filter_by(login=login).one()
        except NoResultFound:
            return None
        else:
            return user if user.check_password(plaintext_password) else None

    @hybrid_method
    def active_memberships(self, when=None):
        if when is None:
            now = session.utcnow()
            when = single(now)
        return [m for m in self.memberships
                if when.overlaps(closed(m.begins_at, m.ends_at))]

    @active_memberships.expression
    def active_memberships(cls, when=None):
        return select([Membership]).select_from(
            join(cls, Membership)
        ).where(
            Membership.active(when)
        )

    @hybrid_method
    def active_property_groups(self, when=None):
        return object_session(self).query(
            PropertyGroup
        ).join(
            Membership
        ).filter(
            Membership.active(when),
            Membership.user_id == self.id
        ).all()

    @active_property_groups.expression
    def active_property_groups(cls, when=None):
        return select([PropertyGroup]).select_from(
            join(PropertyGroup,
                 Membership).join(cls)
        ).where(
            Membership.active(when)
        )

    @hybrid_method
    def active_traffic_groups(self, when=None):
        return object_session(self).query(
            TrafficGroup
        ).join(
            Membership
        ).filter(
            Membership.active(when),
            Membership.user_id == self.id
        ).all()

    @active_traffic_groups.expression
    def active_traffic_groups(cls, when=None):
        return select([TrafficGroup]).select_from(
            join(TrafficGroup,
                 Membership).join(cls)
        ).where(
            Membership.active(when)
        )

    @hybrid_method
    def member_of(self, group, when=None):
        return group in self.active_property_groups(when)

    @member_of.expression
    def member_of(cls, group, when=None):
        return exists(
            select([null()]).select_from(
                PropertyGroup.__table__.join(
                    Membership.__table__,
                    PropertyGroup.id == Membership.group_id
                    )
            ).where(
                and_(
                    Membership.user_id == cls.id,
                    PropertyGroup.id == group.id,
                    Membership.active(when)
                )
            )
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
                Property.__table__,
                PropertyGroup.__table__,
                Membership.__table__
            ]
        ).where(
            and_(
                Property.name == prop,
                Property.property_group_id == PropertyGroup.id,
                PropertyGroup.id == Membership.group_id,
                Membership.user_id == cls.id,
                Membership.active(when)
            )
        )
        #.cte("property_granted_select")
        return and_(
            not_(exists(
                property_granted_select.where(
                    Property.granted == false())

            )),
            exists(
                property_granted_select.where(
                    Property.granted == true()
                )
            )
        ).self_group().label("has_property_" + prop)
#
#    def group_intervals(self, group, when=UnboundedInterval):
#

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
            Property.granted,
            Membership.begins_at,
            Membership.ends_at
        ).filter(
            Property.name == name,
            Property.property_group_id == PropertyGroup.id,
            PropertyGroup.id == Membership.group_id,
            Membership.user_id == self.id
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


class Group(IntegerIdModel):
    name = Column(String(255), nullable=False)
    discriminator = Column('type', String(17), nullable=False)
    __mapper_args__ = {'polymorphic_on': discriminator}

    users = relationship(User,
                         secondary=lambda: Membership.__table__,
                         viewonly=True)

    @hybrid_method
    def active_users(self, when=None):
        """
        :param Interval when:
        :rtype: list[User]
        """
        return object_session(self).query(User).join(
            (Membership, Membership.user_id == User.id),
        ).filter(
            Membership.active(when), Membership.group_id == self.id
        ).all()

    @active_users.expression
    def active_users(cls, when=None):
        return select([User]).select_from(
            join(User, Membership).join(cls)
        ).where(
            Membership.active(when)
        )


class Membership(IntegerIdModel):
    begins_at = Column(DateTime, nullable=True, default=functions.utcnow())
    ends_at = Column(DateTime, nullable=True)

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey(Group.id, ondelete="CASCADE"),
                      nullable=False)
    group = relationship(Group, backref=backref("memberships",
                                                cascade="all, delete-orphan",
                                                order_by='Membership.id'))

    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                     nullable=False)
    user = relationship(User, backref=backref("memberships",
                                              cascade="all, delete-orphan"))

    __table_args = (
        CheckConstraint("begins_at IS NULL OR "
                        "ends_at IS NULL OR "
                        "begins_at <= ends_at")
    )

    @hybrid_method
    def active(self, when=None):
        """
        Tests if the membership overlaps with a given interval. If no interval
        is given, it tests if the membership is active right now.
        :param Interval when: interval in which the membership
        :rtype: bool
        """
        if when is None:
            now = object_session(self).query(functions.utcnow()).scalar()
            when = single(now)

        return when.overlaps(closed(self.begins_at, self.ends_at))

    @active.expression
    def active(cls, when=None):
        """
        Tests if memberships overlap with a given interval. If no interval is
        given, it tests if the memberships are active right now.
        :param Interval when:
        :return:
        """
        if when is None:
            now = session.utcnow()
            when = single(now)

        return and_(
            or_(cls.begins_at == null(), literal(when.end) == null(),
                cls.begins_at <= literal(when.end)),
            or_(literal(when.begin) == null(), cls.ends_at == null(),
                literal(when.begin) <= cls.ends_at)
        ).label("active")

    @validates('ends_at')
    def validate_ends_at(self, _, value):
        if value is None:
            return value
        if self.begins_at is not None:
            assert value >= self.begins_at,\
                "begins_at must be before ends_at"
        return value

    @validates('begins_at')
    def validate_begins_at(self, _, value):
        if value is None:
            return value
        if self.ends_at is not None:
            assert value <= self.ends_at,\
                "begins_at must be before ends_at"
        return value

    def disable(self):
        now = session.utcnow()
        if self.begins_at is not None and self.begins_at > now:
            self.ends_at = self.begins_at
        else:
            self.ends_at = now


class PropertyGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'property_group'}
    id = Column(Integer, ForeignKey(Group.id), primary_key=True,
                nullable=False)
    property_grants = association_proxy(
        "properties", "granted",
        creator=lambda k, v: Property(name=k, granted=v)
    )


class Property(IntegerIdModel):
    name = Column(String(255), nullable=False)
    granted = Column(Boolean, nullable=False)

    # many to one from Property to PropertyGroup
    # nullable=True
    property_group_id = Column(Integer, ForeignKey(PropertyGroup.id),
                               nullable=False)
    #TODO prüfen, ob cascade Properties löscht, wenn zugehörige PGroup deleted
    property_group = relationship(
        PropertyGroup,
        backref=backref("properties", cascade="all, delete-orphan",
                        collection_class=attribute_mapped_collection("name"))
    )


class TrafficGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'traffic_group'}
    id = Column(Integer, ForeignKey(Group.id), primary_key=True,
                nullable=False)
    credit_limit = Column(BigInteger, nullable=False)
    credit_interval = Column(Interval, nullable=False)
    credit_amount = Column(BigInteger, nullable=False)
    initial_credit_amount = Column(BigInteger, nullable=False)


unix_account_uid_seq = Sequence('unix_account_uid_seq', start=1000, metadata=ModelBase.metadata)


class UnixAccount(IntegerIdModel):
    uid = Column(Integer, nullable=False, unique=True,
                        server_default=unix_account_uid_seq.next_value())
    gid = Column(Integer, nullable=False, default=100)
    login_shell = Column(String, nullable=False, default="/bin/bash")
    home_directory = Column(String, nullable=False, unique=True)
