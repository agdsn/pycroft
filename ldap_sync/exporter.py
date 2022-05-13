import logging
import os
from collections import Counter, defaultdict, namedtuple
from distutils.util import strtobool
from itertools import chain
from typing import Iterable

from . import logger
from .db import UserProxyType, GroupProxyType, PropertyProxyType
from .record import UserRecord, GroupRecord, RecordState


class LdapExporter:
    """The ldap Exporter

    Usage:

        >>> from ldap_sync.record import UserRecord
        >>> record = UserRecord(dn='cn=admin,ou=users,dc=agdsn,dc=de', attrs={})
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
    def __init__(self, current, desired):
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
        current = []
        current.append(UserRecord.from_ldap_record(x) for x in ldap_users)
        if ldap_groups:
            current.append(GroupRecord.from_ldap_record(x) for x in ldap_groups)
        if ldap_properties:
            current.append(GroupRecord.from_ldap_record(x) for x in ldap_properties)


        desired = []
        desired.append(UserRecord.from_db_user(x.User, user_base_dn, x.should_be_blocked)
                    for x in db_users)

        # Remove members that are not exported from groups/properties
        exported_users = { u.User.login for u in db_users }

        if db_groups:
            desired.append(
                GroupRecord.from_db_group(x.Group.name,
                                          (m for m in x.members if m in exported_users),
                                          group_base_dn, user_base_dn)
                for x in db_groups)
        if db_properties:
            desired.append(
                GroupRecord.from_db_group(x.name,
                                          (m for m in x.members if m in exported_users),
                                          property_base_dn, user_base_dn)
                for x in db_properties)

        return cls(chain.from_iterable(current), chain.from_iterable(desired))

    def compile_actions(self):
        """Consolidate current and desired records into necessary actions"""
        if self.actions:
            raise RuntimeError("Actions can only be compiled once")
        for state in self.states_dict.values():
            self.actions.append(state.desired - state.current)

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



_sync_config = namedtuple(
    'LdapSyncConfig',
    ['host', 'port', 'use_ssl', 'ca_certs_file', 'ca_certs_data', 'bind_dn',
     'bind_pw', 'base_dn', 'db_uri', 'required_property']
)


def _from_environ_or_defaults(key, defaults):
    try:
        return os.environ[f'PYCROFT_LDAP_{key.upper()}']
    except KeyError as e:
        if key not in defaults:
            print("defaults:", defaults)
            raise ValueError(f"Missing configuration key {key}") from e
        return defaults[key]


def get_config(**defaults):
    config_dict = {
        # e.g. 'host': 'PYCROFT_LDAP_HOST'
        key: _from_environ_or_defaults(key, defaults)
        for key in _sync_config._fields if key != 'db_uri'
    }
    config_dict['port'] = int(config_dict['port'])
    if 'use_ssl' in config_dict:
        config_dict['use_ssl'] = bool(strtobool(config_dict['use_ssl']))
    config_dict['db_uri'] = os.environ['PYCROFT_DB_URI']
    config = _sync_config(**config_dict)

    return config


def get_config_or_exit(**defaults):
    try:
        return get_config(**defaults)
    except KeyError as exc:
        logger.critical("%s not set, quitting", exc.args[0])
        exit()
