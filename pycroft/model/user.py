# -*- coding: utf-8 -*-
"""
    pycroft.model.user
    ~~~~~~~~~~~~~~

    This module contains the class User.

    :copyright: (c) 2011 by AG DSN.
"""
from flaskext.login import UserMixin
from base import ModelBase
from sqlalchemy import ForeignKey
from sqlalchemy import Column
from sqlalchemy.orm import backref, relationship, validates
from sqlalchemy.types import DateTime, Integer
from sqlalchemy.types import String
import re
from pycroft.helpers.user_helper import hash_password, verify_password



class User(ModelBase, UserMixin):
    login = Column(String(40), nullable=False)
    name = Column(String(255), nullable=False)
    registration_date = Column(DateTime, nullable=False)
    passwd_hash = Column(String)

    # many to one from User to Room
    room = relationship("Room", backref=backref("users", order_by='User.id'))
    room_id = Column(Integer, ForeignKey("room.id"), nullable=False)

    login_regex = re.compile("^[a-z][a-z0-9_]{1,20}[a-z0-9]$")
    name_regex = re.compile("^(([a-z]{1,5}|[A-Z][a-z0-9]+)\\s)*"\
                            "([A-Z][a-z0-9]+)((-|\\s)"\
                            "[A-Z][a-z0-9]+|\\s[a-z]{1,5})*$")

    @validates('login')
    def validate_login(self, key, value):
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
