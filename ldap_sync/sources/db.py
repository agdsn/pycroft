#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
ldap_sync.sources.db
~~~~~~~~~~~~~~~~~~~~

This module is responsible for fetching the list of desired records from the DB.
Most prominently:

* :func:`fetch_db_users`
* :func:`fetch_db_properties`
* :func:`fetch_db_groups`

"""
import typing
from typing import NamedTuple

from sqlalchemy import and_, func, select, join, text, literal
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import scoped_session, sessionmaker, joinedload, foreign, Session

from pycroft.model import create_engine
from pycroft.model.property import CurrentProperty
from pycroft.model.session import set_scoped_session, session as global_session
from pycroft.model.user import User, Group, Membership
from .. import logger, conversion
from ..concepts import types
from ..concepts.record import UserRecord, GroupRecord


def establish_and_return_session(connection_string: str) -> Session:
    engine = create_engine(connection_string)
    set_scoped_session(typing.cast(Session, scoped_session(sessionmaker(bind=engine))))
    return typing.cast(Session, global_session)  # from pycroft.model.session


class _UserProxyType(NamedTuple):
    """Representation of a user as returned by :func:`_fetch_db_users`."""

    User: User
    should_be_blocked: bool


def _fetch_db_users(
    session: Session, required_property: str | None = None
) -> list[_UserProxyType]:
    """Fetch users to be synced, plus whether ``ldap_login_enabled`` is set.

    If the `` ldap_login_enabled`` flag is not present,
    we interpret this as ``should_be_blocked``.

    :param session: The SQLAlchemy session to use
    :param str required_property: the property required to export users

    :returns: An iterable of ``(User, should_be_blocked)`` ResultProxies
        having the property ``required_property`` and a unix_account.
    """
    _warn_users_without_accounts(session, required_property)

    # used for second join against CurrentProperty
    not_blocked_property = CurrentProperty.__table__.alias("ldap_login_enabled")

    return typing.cast(
        list[_UserProxyType],
        # Grab all users with the required property
        session.query(User)
        .options(joinedload(User.unix_account))
        .join(User.current_properties)
        .filter(
            (CurrentProperty.property_name == required_property)
            if required_property
            else literal(True),
            User.unix_account_id.is_not(None),
        )
        # additional info:
        #  absence of `ldap_login_enabled` property → should_be_blocked
        .add_columns(
            not_blocked_property.c.property_name.is_(None).label("should_be_blocked")
        )
        .outerjoin(
            not_blocked_property,
            and_(
                User.id == foreign(not_blocked_property.c.user_id),
                ~not_blocked_property.c.denied,
                not_blocked_property.c.property_name == "ldap_login_enabled",
            ),
        )
        .all(),
    )


def fetch_db_users(
    session: Session,
    base_dn: types.DN,
    required_property: str | None = None,
) -> typing.Iterator[UserRecord]:
    """Fetch the users to be synced (in the form of :class:`UserRecords <UserRecord>`).

    :param session: the SQLAlchemy database session
    :param base_dn: the user base dn
    :param required_property: which property the users need to currently have in order to be synced
    """
    for res in _fetch_db_users(session, required_property=required_property):
        yield conversion.db_user_to_record(res.User, base_dn, res.should_be_blocked)


def _warn_users_without_accounts(
    session: Session,
    required_property: str | None
) -> None:
    no_unix_account_stmt = select().select_from(User)
    # two method calls don't count as method chaining
    # fmt: off
    if required_property:
        no_unix_account_stmt = no_unix_account_stmt \
            .join(User.current_properties) \
            .filter(CurrentProperty.property_name == required_property)
    no_unix_account_stmt = no_unix_account_stmt \
        .filter(User.unix_account_id.is_(None)) \
        .add_columns(func.count())
    # fmt: on

    if not (count := session.scalar(no_unix_account_stmt)):
        return

    if required_property:
        logger.warning(
            "%s users have the '%s' property but not a unix_account",
            count,
            required_property,
        )
    else:
        logger.warning(
            "%s users applicable to exporting don't have a unix_account",
            count,
        )


class _GroupProxyType(NamedTuple):
    """Representation of a group as returned by :func:`_fetch_db_groups`."""

    Group: Group
    members: list[str]


def _fetch_db_groups(session: Session) -> list[_GroupProxyType]:
    """Fetch all groups together with all members

    :param session: The SQLAlchemy session to use

    :returns: An iterable of `(Group, members)` ResultProxies.
    """
    return typing.cast(
        list[_GroupProxyType],
        Group.q
        # uids of the members of the group
        .add_columns(
            func.coalesce(
                select(func.array_agg(User.login))
                .select_from(join(Membership, User))
                .where(Membership.group_id == Group.id)
                .where(Membership.active_during.contains(func.current_timestamp()))
                .group_by(Group.id)
                .scalar_subquery(),
                func.cast(literal("{}"), postgresql.ARRAY(User.login.type)),
            ).label("members")
        ).all(),
    )


def fetch_db_groups(
    session: Session,
    base_dn: types.DN,
    user_base_dn: types.DN,
) -> typing.Iterator[GroupRecord]:
    """Fetch the groups to be synced (in the form of :class:`GroupRecords <GroupRecord>`).

    :param session: the SQLAlchemy database session
    :param base_dn: the group base dn
    :param user_base_dn: the base dn of users. Used to infer DNs of the group's members.
    """
    for res in _fetch_db_groups(session):
        yield conversion.db_group_to_record(
            name=res.Group.name,
            members=res.members,
            base_dn=base_dn,
            user_base_dn=user_base_dn,
        )


class _PropertyProxyType(NamedTuple):
    """Representation of a property as returned by :func:`_fetch_db_properties`."""

    name: str
    members: list[str]


def _fetch_db_properties(session: Session) -> list[_PropertyProxyType]:
    """Fetch the groups who should be synced.

    Explicitly, this returns everything in :ref:`EXPORTED_PROPERTIES` together with
    the current users having the respective property as members.

    :param session: The SQLAlchemy session to use

    :returns: An iterable of `(property_name, members)` ResultProxies.
    """
    properties = session.execute(
        select(
            CurrentProperty.property_name.label("name"),
            func.array_agg(User.login).label("members"),
        )
        .select_from(
            join(CurrentProperty, User, onclause=CurrentProperty.user_id == User.id)
        )
        .where(CurrentProperty.property_name.in_(EXPORTED_PROPERTIES))
        .group_by(CurrentProperty.property_name)
    ).fetchall()

    missing_properties = EXPORTED_PROPERTIES - {p.name for p in properties}
    # Return mutable copy instead of SQLAlchemy's immutable RowProxy
    return [_PropertyProxyType(p.name, p.members) for p in properties] + [
        _PropertyProxyType(p, []) for p in missing_properties
    ]


def fetch_db_properties(
    session: Session,
    base_dn: types.DN,
    user_base_dn: types.DN,
) -> typing.Iterator[GroupRecord]:
    """Fetch the properties to be synced (in the form of :class:`GroupRecords <GroupRecord>`).

    :param session: the SQLAlchemy database session
    :param base_dn: the property base dn
    :param user_base_dn: the base dn of users. Used to infer DNs of the users who are currently
        carrying this property.
    """
    for res in _fetch_db_properties(session):
        yield conversion.db_group_to_record(
            name=res.name,
            members=res.members,
            base_dn=base_dn,
            user_base_dn=user_base_dn,
        )


EXPORTED_PROPERTIES = frozenset(
    [
        "network_access",
        "mail",
        "traffic_limit_exceeded",
        "payment_in_default",
        "violation",
        "member",
        "ldap_login_enabled",
        "userdb",
        "membership_fee",
    ]
)
