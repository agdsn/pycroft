# -*- coding: utf-8 -*-
# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.user
    ~~~~~~~~~~~~~~

    This module contains the class User.

    :copyright: (c) 2011 by AG DSN.
"""
from flask.ext.login import UserMixin
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from base import ModelBase
from sqlalchemy import ForeignKey, Column, and_, or_, func, DateTime, Integer, \
    String, Boolean, select, exists
from sqlalchemy.orm import backref, relationship, validates
import re
from sqlalchemy.orm.util import has_identity
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime
from pycroft.model.dormitory import Room
from pycroft.model.property import Membership, Property, PropertyGroup, TrafficGroup
from pycroft.model.session import session
from pycroft.helpers.user import hash_password, verify_password

class User(ModelBase, UserMixin):
    login = Column(String(40), nullable=False)
    name = Column(String(255), nullable=False)
    registration_date = Column(DateTime, nullable=False)
    passwd_hash = Column(String)
    email = Column(String(255), nullable=True)


    # many to one from User to Room
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False)
    room = relationship("Room", backref=backref("users", order_by='User.id'),
                        primaryjoin=lambda: and_(User.is_away == False,
                                                 Room.id == User.room_id))

    traffic_groups = relationship("TrafficGroup",
        secondary=Membership.__tablename__,
        primaryjoin="User.id==Membership.user_id",
        secondaryjoin="Membership.group_id==TrafficGroup.id",
        foreign_keys=[Membership.user_id, Membership.group_id],
        viewonly=True)

    active_traffic_groups = relationship("TrafficGroup",
        secondary=Membership.__tablename__,
        primaryjoin="User.id==Membership.user_id",
        secondaryjoin=and_(Membership.group_id==TrafficGroup.id, Membership.active),
        foreign_keys=[Membership.user_id, Membership.group_id],
        viewonly=True)

    property_groups = relationship("PropertyGroup",
        secondary=Membership.__tablename__,
        primaryjoin="User.id==Membership.user_id",
        secondaryjoin="Membership.group_id==PropertyGroup.id",
        foreign_keys=[Membership.user_id, Membership.group_id],
        viewonly=True)

    active_property_groups = relationship("PropertyGroup",
        secondary=Membership.__tablename__,
        primaryjoin="User.id==Membership.user_id",
        secondaryjoin=and_(Membership.group_id==PropertyGroup.id, Membership.active),
        foreign_keys=[Membership.user_id, Membership.group_id],
        viewonly=True)

    login_regex = re.compile("^[a-z][a-z0-9_]{1,20}[a-z0-9]$")
    email_regex = re.compile(r"^[a-zA-Z0-9]+(?:(?:-|_|\.)[a-zA-Z0-9]+)*"
                             r"@(?:[a-zA-Z0-9]+(?:\.|-))+[a-zA-Z]+$")

    blocked_logins = ["root", "daemon", "bin", "sys", "sync", "games", "man",
                      "lp", "mail", "news", "uucp", "proxy", "majordom",
                      "postgres", "wwwadmin", "backup",	"msql", "operator",
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
        user = User.q.filter(User.login == login).first()
        if user is not None:
            if user.check_password(plaintext_password):
                return user
        return None

    @hybrid_method
    def has_property(self, property_name):
        for group in self.active_property_groups:
            for prop in group.properties:
                if prop.name == property_name:
                    return True
        return False

    @has_property.expression
    def has_property(self, prop):
        now = datetime.now()
        return exists(
            select(["1"], from_obj=[
                Property.__table__,
                PropertyGroup.__table__,
                Membership.__table__])
            .where(and_(
                Property.name == prop,
                Property.property_group_id == PropertyGroup.id,
                PropertyGroup.id == Membership.group_id,
                Membership.user_id == self.id,
                or_(Membership.start_date == None, Membership.start_date <= now),
                or_(Membership.end_date == None, Membership.end_date > now)
            )
            )
        )
