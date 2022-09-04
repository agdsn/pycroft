"""
ldap_sync.exporter
~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

import logging
import typing
from collections import Counter, defaultdict
from typing import Iterable, Iterator

import ldap3

from . import logger
from .concepts import action, types
from .conversion import (
    db_user_to_record,
    db_group_to_record,
    ldap_group_to_record,
    ldap_user_to_record,
)
from .execution import execute_real
from ldap_sync.concepts.record import RecordState, Record
from .record_diff import diff_records
from .sources.db import UserProxyType, GroupProxyType, PropertyProxyType


def iter_current_records(
    ldap_users: Iterable[types.LdapRecord],
    ldap_groups: Iterable[types.LdapRecord],
    ldap_properties: Iterable[types.LdapRecord],
) -> Iterator[Record]:
    yield from (ldap_user_to_record(u) for u in ldap_users)
    yield from (ldap_group_to_record(g) for g in ldap_groups)
    yield from (ldap_group_to_record(p) for p in ldap_properties)


def iter_desired_records(
    db_users: Iterable[UserProxyType],
    db_groups: Iterable[GroupProxyType],
    db_properties: Iterable[PropertyProxyType],
    user_base_dn: types.DN,
    group_base_dn: types.DN,
    property_base_dn: types.DN,
) -> Iterator[Record]:
    # restrict members of groups/properties to those actually exported to the LDAP
    exported_users = {u.User.login for u in db_users}
    for u in db_users:
        yield db_user_to_record(u.User, user_base_dn, u.should_be_blocked)
    for g in db_groups:
        yield db_group_to_record(
            name=g.Group.name,
            members=(m for m in g.members if m in exported_users),
            base_dn=group_base_dn,
            user_base_dn=user_base_dn,
        )
    for p in db_properties:
        yield db_group_to_record(
            name=p.name,
            members=(m for m in p.members if m in exported_users),
            base_dn=property_base_dn,
            user_base_dn=user_base_dn,
        )


TExporter = typing.TypeVar("TExporter", bound="LdapExporter")


class LdapExporter:
    """The ldap Exporter

    Usage:

        >>> from ldap_sync.record import UserRecord
        >>> from ldap_sync.types import DN
        >>> record = UserRecord(dn=DN('cn=admin,ou=users,dc=agdsn,dc=de'), attrs={})
        >>> exporter = LdapExporter(current=[], desired=[record])
        >>> exporter.compile_actions()
        >>> exporter.execute_all()

    Since the desired state is to be represented by a postgres
    database and the current state by the LDAP being synced to,
    :py:meth:`from_orm_objects_and_ldap_result` is there to not
    have to convert the entries to :class:`Records <Record>` manually.

    :param current: The records currently in the system
    :param desired: The records we want to be in the system
    """

    def __init__(self, current: Iterable[Record], desired: Iterable[Record]) -> None:
        self.states_dict: dict[types.DN, RecordState] = defaultdict(RecordState)
        l = -1
        for l, record in enumerate(current, 1):
            self.states_dict[record.dn].current = record
        logger.info("Gathered %d records of current state", l)

        for l, record in enumerate(desired, 1):
            self.states_dict[record.dn].desired = record
        logger.info("Gathered %d records of desired state", l)

        self.actions: list[action.Action] = []

    @classmethod
    def from_orm_objects_and_ldap_result(
        cls: type[TExporter],
        ldap_users: Iterable[types.LdapRecord],
        db_users: Iterable[UserProxyType],
        user_base_dn: types.DN,
        ldap_groups: Iterable[types.LdapRecord] | None = None,
        db_groups: Iterable[GroupProxyType] | None = None,
        group_base_dn: types.DN | None = None,
        ldap_properties: Iterable[types.LdapRecord] | None = None,
        db_properties: Iterable[PropertyProxyType] | None = None,
        property_base_dn: types.DN = None,
    ) -> TExporter:
        """Construct an exporter instance with non-raw parameters

        :param ldap_users: An iterable of records as returned by :func:`fetch_current_ldap_users`.
        :param db_users: An iterable of sqlalchemy result proxies as returned by :func:`fetch_users_to_sync`.
        :param user_base_dn:
        :param ldap_groups: An iterable of records as returned by :func:`fetch_current_ldap_groups`.
        :param db_groups: An iterable of sqlalchemy result proxies as returned by :func:`fetch_groups_to_sync`.
        :param group_base_dn:
        :param ldap_properties: An iterable of records as returned by :py:func:`fetch_current_ldap_properties`.
        :param db_properties: An iterable of sqlalchemy result proxies as returned by :func:`fetch_properties_to_sync`.
        :param property_base_dn:
        :return:
        """
        import warnings
        warnings.warn("Use the explicit constructor and iter_{current,desired}_records instead",
                      DeprecationWarning)
        return cls(
            current=iter_current_records(
                ldap_users, ldap_groups or iter(()), ldap_properties or iter(())
            ),
            desired=iter_desired_records(
                db_users,
                db_groups or iter(()),
                db_properties or iter(()),
                user_base_dn,
                group_base_dn,
                property_base_dn,
            ),
        )

    def compile_actions(self) -> None:
        """Consolidate current and desired records into necessary actions"""
        if self.actions:
            raise RuntimeError("Actions can only be compiled once")
        for state in self.states_dict.values():
            self.actions.append(diff_records(current=state.current, desired=state.desired))

    def execute_all(self, *a: typing.Any, **kw: typing.Any) -> None:
        for action in self.actions:
            execute_real(action, *a, **kw)


#### TODO move to `ldap` (or `ldap_fetch`? or `sources.ldap`?) module


def add_stdout_logging(logger: logging.Logger, level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(levelname)s %(asctime)s %(name)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(level)


def sync_all(
    connection: ldap3.Connection,
    ldap_users: Iterable[types.LdapRecord],
    db_users: Iterable[UserProxyType],
    user_base_dn: types.DN,
    ldap_groups: Iterable[types.LdapRecord] | None = None,
    db_groups: Iterable[GroupProxyType] | None = None,
    group_base_dn: types.DN | None = None,
    ldap_properties: Iterable[types.LdapRecord] | None = None,
    db_properties: Iterable[PropertyProxyType] | None = None,
    property_base_dn: types.DN | None = None,
) -> None:
    """Convert objects to Records, diff them, and execute the inferred actions.

    :param connection: the connection to use for execution
    :param ldap_users: the users currently in the ldap
    :param db_users: the users currently in the db
    :param user_base_dn: the user base DN
    :param ldap_groups: the groups currently in the ldap
    :param db_groups: the groups currently in the ldap
    :param group_base_dn: the group base DN. Has to be set if one of
        :paramref:`ldap_groups` or :paramref:`db_groups` is set.
    :param ldap_properties: the properties currently in the ldap
    :param db_properties: the properties currently in the db
    :param property_base_dn: the property base DN. Has to be set if one of
        :paramref:`ldap_properties` or :paramref:`db_groups` is set.
    """
    from . import record_diff

    desired_records = iter_desired_records(
        db_users,
        db_groups or iter(()),
        db_properties or iter(()),
        user_base_dn,
        group_base_dn,
        property_base_dn,
    )
    current_records = iter_current_records(
        ldap_users, ldap_groups or iter(()), ldap_properties or iter(())
    )
    actions_by_dn = record_diff.bulk_diff_records(
        current_records=current_records,
        desired_records=desired_records,
    )

    action_types = Counter(type(a).__name__ for a in actions_by_dn)
    logger.info("Compiled %s actions (%s)", len(actions_by_dn),
                ", ".join(f"{type_}: {count}"
                          for type_, count in action_types.items()))

    logger.info("Executing actions")
    for action in actions_by_dn.values():
        logger.debug("Executing %s", action)
        execute_real(action, connection=connection)
    logger.info("Execution finished.")
