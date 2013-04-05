# -*- coding: utf-8 -*-
"""
    pycroft.model.user
    ~~~~~~~~~~~~~~

    This module contains the class User.

    :copyright: (c) 2011 by AG DSN.
"""
from flask.ext.login import UserMixin
from base import ModelBase
from sqlalchemy import ForeignKey, Column, and_, or_, func, DateTime, Integer, \
    String, Boolean
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
    # room = relationship("Room")
    room = relationship("Room", backref=backref("users", order_by='User.id'),
        # primaryjoin="and_(User.is_away== False, Room.id==User.room_id)")
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

    @hybrid_property
    def is_away(self):
        for group in self.active_property_groups:
            if group.name == "tmpAusgezogen":
                return True
        else: return False

    @is_away.expression
    def is_away(cls):
        now = datetime.now()

        return session.query(
            func.count(Membership.id) > 0
        ).join(
            PropertyGroup
        ).filter(
            PropertyGroup.name == "tmpAusgezogen",
            Membership.user_id == cls.id,
            or_(Membership.start_date == None,
                Membership.start_date <= now),
            or_(Membership.end_date == None,
                Membership.end_date > now)
        ).scalar()
