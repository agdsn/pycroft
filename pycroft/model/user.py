# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.user
    ~~~~~~~~~~~~~~~~~~

    This module contains the class User.

    :copyright: (c) 2011 by AG DSN.
"""
from __future__ import annotations

import re
import typing
from datetime import timedelta, date, datetime

from flask_login import UserMixin
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer,
    String, and_, exists, join, null, select, Sequence,
    Date, func, UniqueConstraint, Index, text, event)
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.ext.hybrid import hybrid_method, hybrid_property
from sqlalchemy.orm import backref, object_session, relationship, validates, \
    declared_attr
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.util import has_identity

from pycroft.helpers.interval import single, Interval, closedopen
from pycroft.helpers.user import hash_password, verify_password, \
    cleartext_password, \
    clear_password_prefix
from pycroft.helpers import utc
from pycroft.model import session, ddl
from pycroft.model.address import Address, address_remove_orphans
from pycroft.model.base import ModelBase, IntegerIdModel
from pycroft.model.exc import PycroftModelException
from pycroft.model.facilities import Room
from pycroft.model.types import DateTimeTz, TsTzRange

manager = ddl.DDLManager()


class IllegalLoginError(PycroftModelException, ValueError):
    pass


class IllegalEmailError(PycroftModelException, ValueError):
    pass


class BaseUser:
    id = Column(Integer, primary_key=True)
    login = Column(String(40), nullable=False, unique=True)
    name = Column(String(255), nullable=False)
    registered_at = Column(DateTimeTz, nullable=False)
    passwd_hash = Column(String)
    email = Column(String(255), nullable=True)
    email_confirmed = Column(Boolean, server_default="False", nullable=False)
    email_confirmation_key = Column(String, nullable=True)
    birthdate = Column(Date, nullable=True)

    # ForeignKey to Tenancy.person_id / swdd_vv.person_id, but cannot reference view
    swdd_person_id = Column(Integer, nullable=True)

    # many to one from User to Room
    @declared_attr
    def room_id(self):
        return Column(Integer, ForeignKey("room.id", ondelete="SET NULL"),
                      nullable=True, index=True)

    login_regex = re.compile(r"""
            ^
            # Must begin with a lowercase character
            [a-z]
            # Can continue with lowercase characters, numbers and some punctuation
            # but between punctuation characters must be characters or numbers
            (?:[.-]?[a-z0-9])+$
            """, re.VERBOSE)
    login_regex_ci = re.compile(login_regex.pattern, re.VERBOSE | re.IGNORECASE)
    email_regex = re.compile(r"^[a-zA-Z0-9!#$%&'*+\-/=?^_`{|}~]+"
                             r"(?:\.[a-zA-Z0-9!#$%&'*+\-/=?^_`{|}~]+)*"
                             r"@(?:[a-zA-Z0-9]+(?:\.|-))+[a-zA-Z]+$")

    blocked_logins = {"abuse", "admin", "administrator", "autoconfig",
                      "broadcasthost", "root", "daemon", "bin", "sys", "sync",
                      "games", "man", "hostmaster", "imap", "info", "is",
                      "isatap", "it", "localdomain", "localhost",
                      "lp", "mail", "mailer-daemon", "news", "uucp", "proxy",
                      # ground control to
                      "majordom", "marketing", "mis", "noc", "website", "api",
                      "noreply", "no-reply",
                      "pop", "pop3", "postmaster",
                      "postgres", "sales", "smtp", "ssladmin", "status",
                      "ssladministrator", "sslwebmaster", "support",
                      "sysadmin", "usenet", "webmaster", "wpad", "www",
                      "wwwadmin", "backup", "msql", "operator", "user",
                      "ftp", "ftpadmin", "guest", "bb", "nobody", "www-data",
                      "bacula", "contact", "email", "privacy", "anonymous",
                      "web", "git", "username", "log", "login", "help", "name"}

    login_character_limit = 22

    @validates('login')
    def validate_login(self, _, value):
        if not self.login_regex.match(value):
            raise IllegalLoginError(
                f"Illegal login '{value}': Logins must begin with a lower case "
                "letter and may be followed by lower case letters, digits or "
                "punctuation (dash and dot). Punctuation "
                "characters must be separated by at least on letter or digit."
            )
        if value in self.blocked_logins:
            raise IllegalLoginError(
                f"Illegal login '{value}': This login is blocked and may not be used."
            )
        if len(value) > self.login_character_limit:
            raise IllegalLoginError(
                f"Illegal login '{value}': Logins are limited to at most"
                f" {self.login_character_limit} characters."
            )
        return value

    @validates('email')
    def validate_email(self, _, value):
        if value is None:
            return value
        if not self.email_regex.match(value):
            raise IllegalEmailError(f"Illegal email '{value}'")
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
    def password(self, value: str):
        self.passwd_hash = hash_password(value)


class User(ModelBase, BaseUser, UserMixin):
    wifi_passwd_hash = Column(String)

    # one to one from User to Account
    account_id = Column(Integer, ForeignKey("account.id"), nullable=False, index=True)
    account = relationship("Account", backref=backref("user", uselist=False, viewonly=True))

    unix_account_id = Column(Integer, ForeignKey('unix_account.id'), nullable=True, unique=True)
    unix_account: UnixAccount = relationship('UnixAccount')  # backref not really needed.

    address_id = Column(Integer, ForeignKey(Address.id), index=True, nullable=False)
    address = relationship(Address, backref=backref("inhabitants", viewonly=True))

    room = relationship("Room", backref=backref("users", viewonly=True), sync_backref=False)

    email_forwarded = Column(Boolean, server_default='True', nullable=False)

    password_reset_token = Column(String, nullable=True)

    def __init__(self, **kwargs: typing.Any) -> None:
        password = kwargs.pop('password', None)
        wifi_password = kwargs.pop('password', None)
        super().__init__(**kwargs)
        if password is not None:
            self.password = password
        if wifi_password is not None:
            self.wifi_password = wifi_password

    @hybrid_property
    def has_custom_address(self):
        """Whether the user's address differs from their room's address.

        If no room is assigned, returns ``False``.
        """
        return self.address != self.room.address if self.room else False

    # noinspection PyMethodParameters
    @has_custom_address.expression
    def has_custom_address(cls):
        return and_(
            cls.room_id.isnot(None),
            exists(select(null())
                  .select_from(Room)
                  .where(Room.id == cls.room_id)
                  .where(Room.address_id != cls.address_id))
        )

    @validates('login')
    def validate_login(self, _, value):
        assert not has_identity(
            self), "user already in the database - cannot change login anymore!"

        return super().validate_login(_, value)

    property_groups = relationship("PropertyGroup",
                                   secondary=lambda: Membership.__table__,
                                   viewonly=True)

    @hybrid_method
    def traffic_for_days(self, days):
        from pycroft.model.traffic import TrafficVolume

        return sum(v.amount for v in TrafficVolume.q.filter_by(user_id=self.id)
                   .filter(TrafficVolume.timestamp >= (session.utcnow() - timedelta(days-1)).date()))

    @traffic_for_days.expression
    def traffic_for_days(self, days):
        from pycroft.model.traffic import TrafficVolume

        return select(func.sum(TrafficVolume.amount).label('amount')) \
            .where(
            TrafficVolume.timestamp >= (session.utcnow() - timedelta(days-1)).date()
            .where(TrafficVolume.user_id == self.id))

    #: This is a relationship to the `current_property` view filtering out
    #: the entries with `denied=True`.
    current_properties = relationship(
        'CurrentProperty',
        primaryjoin='and_(User.id == foreign(CurrentProperty.user_id),'
                    '~CurrentProperty.denied)',
        order_by='CurrentProperty.property_name',
        viewonly=True
    )
    #: This is a relationship to the `current_property` view ignoring the
    #: `denied` attribute.
    current_properties_maybe_denied = relationship(
        'CurrentProperty',
        primaryjoin='User.id == foreign(CurrentProperty.user_id)',
        order_by='CurrentProperty.property_name',
        viewonly=True
    )

    @property
    def current_properties_set(self) -> set[str]:
        """A type-agnostic property giving the granted properties as a set of string.

        Utilized in the web component's access control mechanism.
        """
        return {p.property_name for p in self.current_properties}

    @property
    def wifi_password(self):
        """Store a hash of a given plaintext passwd for the user.

        """

        if self.wifi_passwd_hash is not None and self.wifi_passwd_hash.startswith(clear_password_prefix):
            return self.wifi_passwd_hash.replace(clear_password_prefix, '', 1)

        raise ValueError("Cleartext password not available.")

    @wifi_password.setter
    def wifi_password(self, value):
        self.wifi_passwd_hash = cleartext_password(value)

    @hybrid_property
    def has_wifi_access(self):
        return self.wifi_passwd_hash is not None

    @staticmethod
    def verify_and_get(login, plaintext_password):
        try:
            user = User.q.filter(User.login == func.lower(login)).one()
        except NoResultFound:
            return None
        else:
            return user if user.check_password(plaintext_password) else None

    current_memberships = relationship(
        'Membership',
        primaryjoin='and_(Membership.user_id==User.id,'
                    '     Membership.active_during.contains(func.current_timestamp()))',
        viewonly=True
    )

    @hybrid_method
    def active_memberships(self, when: Interval | None = None) -> list[Membership]:
        if when is None:
            now = session.utcnow()
            when = single(now)
        return [m for m in self.memberships
                if when.overlaps(m.active_during.closure)]

    @active_memberships.expression
    def active_memberships(cls, when=None):
        return (
            select(Membership)
            .select_from(join(cls, Membership))
            .where(Membership.active_during & when if when
                   else Membership.active_during.contains(func.current_timestamp()))
        )

    @hybrid_method
    def active_property_groups(self, when: Interval | None = None) -> list[PropertyGroup]:
        sess = object_session(self)
        when = when or single(session.utcnow())
        return sess.query(
            PropertyGroup
        ).join(
            Membership
        ).filter(
            Membership.active_during & when,
            Membership.user_id == self.id
        ).all()

    @active_property_groups.expression
    def active_property_groups(cls, when=None):
        return select(PropertyGroup).select_from(
            join(PropertyGroup,
                 Membership).join(cls)
        ).where(
            Membership.active_during & when if when
            else Membership.active_during.contains(func.current_timestamp())
        )

    def member_of(self, group: PropertyGroup, when: Interval | None = None) -> bool:
        return group in self.active_property_groups(when)

    def has_property(self, property_name: str, when: datetime | None = None) -> bool:
        if when is None:
            return property_name in self.current_properties_set

        if isinstance(when, Interval):
            raise PycroftModelException("`has_property` does not accept intervals!")

        # usages in this branch: only wrt `membership_fee` in `estimate_balance` for finance stuff
        prop_granted_flags = [
            group.property_grants[property_name]
            for group in self.active_property_groups(single(when))
            if property_name in group.property_grants
        ]

        # In case of prop_granted_flags = []: Return False
        # Else: Return True if all elements of prop_granted_flags are True
        return all(prop_granted_flags) and any(prop_granted_flags)

    @property
    def permission_level(self) -> int:
        return max((membership.group.permission_level for membership in self.active_memberships()),
                   default=0)

    @property
    def email_internal(self):
        return f"{self.login}@agdsn.me"

    __table_args__ = (UniqueConstraint('swdd_person_id'),)


manager.add_function(
    User.__table__,
    ddl.Function(
        'user_room_change_update_history', [],
        'trigger',
        """
        BEGIN
            IF old.room_id IS DISTINCT FROM new.room_id THEN
                IF old.room_id IS NOT NULL THEN
                    /* User was living in a room before, history entry must be ended */
                    /* active_during is expected to be [) */
                    UPDATE "room_history_entry"
                        SET active_during = active_during - tstzrange(CURRENT_TIMESTAMP, null, '[)')
                        WHERE room_id = old.room_id AND user_id = new.id
                        AND active_during && tstzrange(CURRENT_TIMESTAMP, null, '[)');
                END IF;

                IF new.room_id IS NOT NULL THEN
                    /* User moved to a new room. history entry must be created */
                    INSERT INTO "room_history_entry" (user_id, room_id, active_during)
                        /* We must add one second so that the user doesn't have two entries
                           for the same timestamp */
                        VALUES(new.id, new.room_id, tstzrange(CURRENT_TIMESTAMP, null, '[)'));
                END IF;
            END IF;
            RETURN NULL;
        END;
        """,
        volatility='volatile', strict=True, language='plpgsql'
    )
)

manager.add_trigger(
    User.__table__,
    ddl.Trigger(
        'user_room_change_update_history_trigger',
        User.__table__,
        ('UPDATE', 'INSERT'),
        'user_room_change_update_history()'
    )
)


manager.add_trigger(User.__table__, ddl.Trigger(
    'user_address_cleanup_trigger',
    User.__table__,
    ('UPDATE', 'DELETE'),
    f'{address_remove_orphans.name}()',
))


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
            Membership, Membership.user_id == User.id
        ).filter(
            (Membership.active_during & when) if when
            else Membership.active_during.contains(func.current_timestamp()),
            Membership.group_id == self.id
        ).all()

    @active_users.expression
    def active_users(cls, when=None):
        return select(User).select_from(
            join(User, Membership).join(cls)
        ).where(
            Membership.active_during & when if when
            else Membership.active_during.contains(func.current_timestamp())
        )


class Membership(IntegerIdModel):
    active_during: Interval[utc.DateTimeTz] = Column(TsTzRange, nullable=False)

    def disable(self, at=None):
        if at is None:
            at = object_session(self).scalar(select(func.current_timestamp()))

        self.active_during = self.active_during - closedopen(at, None)
        flag_modified(self, 'active_during')

    # many to one from Membership to Group
    group_id = Column(Integer, ForeignKey(Group.id, ondelete="CASCADE"),
                      nullable=False, index=True)
    group = relationship(Group, backref=backref("memberships",
                                                cascade="all, delete-orphan",
                                                order_by='Membership.id',
                                                cascade_backrefs=False))

    # many to one from Membership to User
    user_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                     nullable=False, index=True)
    user = relationship(User, backref=backref("memberships",
                                              cascade="all, delete-orphan",
                                              cascade_backrefs=False))

    __table_args__ = (
        Index('ix_membership_active_during', 'active_during', postgresql_using='gist'),
        ExcludeConstraint(  # there should be no two memberships…
            (group_id, '='),  # …with the same user
            (user_id, '='),  # …and the same group
            (active_during, '&&'),  # …and overlapping durations
            using='gist'
        ),
    )

@event.listens_for(Membership.__table__, 'before_create')
def create_btree_gist(target, connection, **kw):
    connection.execute(text("create extension if not exists btree_gist"))


class PropertyGroup(Group):
    __mapper_args__ = {'polymorphic_identity': 'property_group'}
    id = Column(Integer, ForeignKey(Group.id), primary_key=True,
                nullable=False)
    permission_level = Column(Integer, nullable=False, default=0)

    property_grants = association_proxy(
        "properties", "granted",
        creator=lambda k, v: Property(name=k, granted=v)
    )
    properties: dict[str, Property]


class Property(IntegerIdModel):
    # TODO add unique key
    name = Column(String(255), nullable=False)
    granted = Column(Boolean, nullable=False)

    # many to one from Property to PropertyGroup
    # nullable=True
    property_group_id = Column(Integer, ForeignKey(PropertyGroup.id),
                               nullable=False, index=True)
    #TODO prüfen, ob cascade Properties löscht, wenn zugehörige PGroup deleted
    property_group = relationship(
        PropertyGroup,
        backref=backref("properties", cascade="all, delete-orphan",
                        collection_class=attribute_mapped_collection("name"))
    )


unix_account_uid_seq = Sequence('unix_account_uid_seq', start=1000,
                                metadata=ModelBase.metadata)


class UnixAccount(IntegerIdModel):
    uid = Column(Integer, nullable=False, unique=True,
                 server_default=unix_account_uid_seq.next_value())
    gid = Column(Integer, nullable=False, default=100)
    login_shell = Column(String, nullable=False, default="/bin/bash")
    home_directory = Column(String, nullable=False, unique=True)


class RoomHistoryEntry(IntegerIdModel):
    active_during: Interval = Column(TsTzRange, nullable=False)

    def disable(self, at=None):
        if at is None:
            at = object_session(self).scalar(select(func.current_timestamp()))

        self.active_during = self.active_during - closedopen(at, None)
        flag_modified(self, 'active_during')

    room_id = Column(Integer, ForeignKey("room.id", ondelete="CASCADE"),
                     nullable=False, index=True)
    room = relationship(Room, backref=backref(name="room_history_entries",
                                              order_by='RoomHistoryEntry.id',
                                              viewonly=True))

    user_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                     nullable=False, index=True)
    user = relationship(User, backref=backref("room_history_entries",
                                              order_by='RoomHistoryEntry.id',
                                              viewonly=True))

    __table_args__ = (
        Index('ix_room_history_entry_active_during', 'active_during', postgresql_using='gist'),
        ExcludeConstraint(  # there should be no two room_history_entries
            (room_id, '='),  # …in the same room
            (user_id, '='),  # …and for the same user
            (active_during, '&&'),  # …and overlapping durations
            using='gist'
        ),
    )


class PreMember(ModelBase, BaseUser):
    login = Column(String(40), nullable=False, unique=False)
    move_in_date = Column(Date, nullable=True)
    previous_dorm = Column(String, nullable=True)
    birthdate = Column(Date, nullable=False)
    passwd_hash = Column(String, nullable=False)

    room = relationship("Room")

    def __init__(self, **kwargs: typing.Any) -> None:
        password = kwargs.pop('password', None)
        super().__init__(**kwargs)
        if password is not None:
            self.password = password

    @property
    def is_adult(self) -> bool:
        today = date.today()

        born = self.birthdate

        age = today.year - born.year - ((today.month, today.day) < (born.month, born.day))

        return age >= 18


manager.register()
