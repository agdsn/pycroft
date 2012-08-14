# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.user
    ~~~~~~~~~~~~~~

    This module contains the class User.

    :copyright: (c) 2011 by AG DSN.
"""
from flask.ext.login import UserMixin
from base import ModelBase
from sqlalchemy import ForeignKey, Column, and_, or_, func, DateTime, Integer, \
    String
from sqlalchemy.orm import backref, relationship, validates
import re
from datetime import datetime
from pycroft.model.properties import Membership, Property, PropertyGroup, TrafficGroup
from pycroft.model.session import session
from pycroft.helpers.user_helper import hash_password, verify_password

class User(ModelBase, UserMixin):
    login = Column(String(40), nullable=False)
    name = Column(String(255), nullable=False)
    registration_date = Column(DateTime, nullable=False)
    passwd_hash = Column(String)

    # many to one from User to Room
    room = relationship("Room", backref=backref("users", order_by=id))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False)

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
    name_regex = re.compile("^(([a-z]{1,5}|[A-Z][a-z0-9]+)\\s)*"
                            "([A-Z][a-z0-9]+)((-|\\s)"
                            "[A-Z][a-z0-9]+|\\s[a-z]{1,5})*$")

    @validates('login')
    def validate_login(self, _, value):
        if not User.login_regex.match(value):
            raise Exception("invalid unix-login!")
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

    def has_property(self, property_name):
        now = datetime.now()
        query = session.query(
            func.count(Property.id).label("property_count")
        ).join(
            (PropertyGroup, PropertyGroup.id == Property.property_group_id)
        ).join(
            (Membership, Membership.group_id == PropertyGroup.id)
        ).filter(
            Property.name == property_name
        ).filter(
            Membership.user_id == self.id
        ).filter(
        # it is important to use == here, "is" does not work
            or_(Membership.start_date == None, Membership.start_date <= now)
        ).filter(
            or_(Membership.end_date == None, Membership.end_date > now)
        )
        result = query.one()

        return result.property_count > 0
