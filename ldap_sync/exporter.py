import logging
from collections import Counter, defaultdict
from typing import Iterable, Iterator

from . import logger, types
from .db import UserProxyType, GroupProxyType, PropertyProxyType
from .record import UserRecord, GroupRecord, RecordState, Record
from .record_diff import diff_records


def iter_current_records(
    ldap_users: Iterable[dict],
    ldap_groups: Iterable[dict],
    ldap_properties: Iterable[dict],
) -> Iterator[Record]:
    yield from (UserRecord.from_ldap_record(u) for u in ldap_users)
    yield from (GroupRecord.from_ldap_record(g) for g in ldap_groups)
    yield from (GroupRecord.from_ldap_record(p) for p in ldap_properties)


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
        yield UserRecord.from_db_user(u.User, user_base_dn, u.should_be_blocked)
    for g in db_groups:
        yield GroupRecord.from_db_group(
            name=g.Group.name,
            members=(m for m in g.members if m in exported_users),
            base_dn=group_base_dn,
            user_base_dn=user_base_dn,
        )
    for p in db_properties:
        yield GroupRecord.from_db_group(
            name=p.name,
            members=(m for m in p.members if m in exported_users),
            base_dn=property_base_dn,
            user_base_dn=user_base_dn,
        )


class LdapExporter:
    """The ldap Exporter

    Usage:

        >>> from ldap_sync.record import UserRecord
        >>> from ldap_sync.types import DN
        >>> record = UserRecord(dn=DN('cn=admin,ou=users,dc=agdsn,dc=de'), attrs={})
        >>> exporter = LdapExporter(current=[], desired=[record])
        >>> exporter.compile_actions()
        >>> exporter.execute_all()

    Since the desired state is to be represented by a postgres
    database and the current state by the LDAP being synced to,
    :py:meth:`from_orm_objects_and_ldap_result` is there to not
    have to convert the entries to :class:`Record`s manually.

    :param iterable current: An iterable of :class:`Record`s
    :param iterable desired: An iterable of the desired
        :class:`Record`s
    """
    def __init__(self, current, desired) -> None:
        self.states_dict = defaultdict(RecordState)
        l = 0
        for l, record in enumerate(current, 1):
            self.states_dict[record.dn].current = record
        logger.info("Gathered %d records of current state", l)

        for l, record in enumerate(desired, 1):
            self.states_dict[record.dn].desired = record
        logger.info("Gathered %d records of desired state", l)

        self.actions = []

    @classmethod
    def from_orm_objects_and_ldap_result(
            cls, ldap_users: dict, db_users: Iterable[UserProxyType], user_base_dn,
            ldap_groups: dict = None, db_groups: Iterable[GroupProxyType] = None,
            group_base_dn=None, ldap_properties: dict = None,
            db_properties: Iterable[PropertyProxyType] = None, property_base_dn=None):
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

    def compile_actions(self):
        """Consolidate current and desired records into necessary actions"""
        if self.actions:
            raise RuntimeError("Actions can only be compiled once")
        for state in self.states_dict.values():
            self.actions.append(diff_records(desired=state.desired, current=state.current))

    def execute_all(self, *a, **kw):
        for action in self.actions:
            action.execute(*a, **kw)


#### TODO move to `ldap` (or `ldap_fetch`? or `sources.ldap`?) module


def add_stdout_logging(logger, level=logging.INFO):
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(levelname)s %(asctime)s %(name)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(level)


def sync_all(connection, ldap_users: dict, db_users: Iterable[UserProxyType], user_base_dn,
             ldap_groups: dict = None, db_groups: Iterable[GroupProxyType] = None,
             group_base_dn=None, ldap_properties: dict = None,
             db_properties: Iterable[PropertyProxyType] = None, property_base_dn=None):
    """Execute the LDAP sync given a connection and state data.

    :param connection: An LDAP connection

    For the other parameters see :func:`LdapExporter.from_orm_objects_and_ldap_result`.
    """
    exporter = LdapExporter.from_orm_objects_and_ldap_result(
        ldap_users, db_users, user_base_dn, ldap_groups, db_groups, group_base_dn, ldap_properties,
        db_properties, property_base_dn)
    logger.info("Initialized LdapExporter (%s unique objects in total) from fetched objects",
                len(exporter.states_dict))

    exporter.compile_actions()
    action_types = Counter(type(a).__name__ for a in exporter.actions)
    logger.info("Compiled %s actions (%s)", len(exporter.actions),
                ", ".join(f"{type_}: {count}"
                          for type_, count in action_types.items()))

    logger.info("Executing actions")
    exporter.execute_all(connection)
    logger.info("Executed %s actions", len(exporter.actions))
