# -*- coding: utf-8; -*-

import logging
import os
import sys
from collections import Counter, defaultdict, namedtuple
from distutils.util import strtobool
from itertools import chain
from typing import Iterable, List, NamedTuple

import ssl
import ldap3
from sqlalchemy import and_, func, select, join
from sqlalchemy.orm import scoped_session, sessionmaker, foreign, joinedload

from pycroft.model import create_engine
from pycroft.model.property import CurrentProperty
from pycroft.model.user import User, Group, Membership
from pycroft.model.session import set_scoped_session, session as global_session
from .record import UserRecord, GroupRecord, RecordState

logger = logging.getLogger('ldap_sync')


class UserProxyType(NamedTuple):
    """Representation of a user as returned by :func:`fetch_users_to_sync`."""
    User: User
    should_be_blocked: bool


class GroupProxyType(NamedTuple):
    """Representation of a group as returned by :func:`fetch_groups_to_sync`."""
    Group: Group
    members: List[str]


class PropertyProxyType(NamedTuple):
    """Representation of a property as returned by :func:`fetch_properties_to_sync`."""
    name: str
    members: List[str]


class LdapExporter(object):
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
    have to convert the entries to :py:cls:`Record`s manually.

    :param iterable current: An iterable of :py:cls:`Record`s
    :param iterable desired: An iterable of the desired
        :py:cls:`Record`s
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


def establish_and_return_session(connection_string):
    engine = create_engine(connection_string)
    set_scoped_session(scoped_session(sessionmaker(bind=engine)))
    return global_session  # from pycroft.model.session


def fetch_users_to_sync(session, required_property=None) -> List[UserProxyType]:
    """Fetch the users who should be synced

    :param session: The SQLAlchemy session to use
    :param str required_property: the property required to export users

    :returns: An iterable of `(User, should_be_blocked)` ResultProxies
        having the property `required_property' and a unix_account.
    """
    if required_property:
        no_unix_account_q = User.q.join(User.current_properties)\
            .filter(CurrentProperty.property_name == required_property,
                    User.unix_account == None)
    else:
        no_unix_account_q = User.q.filter(User.unix_account == None)

    count_exportable_but_no_account = no_unix_account_q.count()

    if required_property:
        logger.warning("%s users have the '%s' property but not a unix_account",
                       count_exportable_but_no_account, required_property)
    else:
        logger.warning("%s users applicable to exporting don't have a unix_account",
                       count_exportable_but_no_account)

    # used for second join against CurrentProperty
    not_blocked_property = CurrentProperty.__table__.alias('ldap_login_enabled')

    return (
        # Grab all users with the required property
        User.q
        .options(joinedload(User.unix_account))
        .join(User.current_properties)
        .filter(CurrentProperty.property_name == required_property,
                User.unix_account != None)

        # additional info:
        #  absence of `ldap_login_enabled` property → should_be_blocked
        .add_column(not_blocked_property.c.property_name.is_(None)
                    .label('should_be_blocked'))
        .outerjoin(
            not_blocked_property,
            and_(User.id == foreign(not_blocked_property.c.user_id),
                 ~not_blocked_property.c.denied,
                 not_blocked_property.c.property_name == 'ldap_login_enabled')
        ).all()
    )


def fetch_groups_to_sync(session) -> List[GroupProxyType]:
    """Fetch the groups who should be synced

    :param session: The SQLAlchemy session to use

    :returns: An iterable of `(Group, members)` ResultProxies.
    """
    return (
        # Grab all users with the required property
        Group.q
        # uids of the members of the group
        .add_column(select([func.array_agg(User.login)])
                .select_from(join(Membership, User))
                .where(Membership.group_id == Group.id).where(Membership.active())
                .group_by(Group.id)
                .as_scalar().label('members'))
        .all()
    )


EXPORTED_PROPERTIES = frozenset([
    'network_access',
    'mail',
    'traffic_limit_exceeded',
    'payment_in_default',
    'violation',
    'member',
    'ldap_login_enabled',
    'userdb',
    'cache_access',
    'membership_fee',
])


def fetch_properties_to_sync(session) -> List[PropertyProxyType]:
    """Fetch the groups who should be synced

    :param session: The SQLAlchemy session to use

    :returns: An iterable of `(property_name, members)` ResultProxies.
    """
    return session.execute(
        # Grab all users with the required property
        select([CurrentProperty.property_name.label('name'),
                func.array_agg(User.login).label('members')])
        .select_from(join(CurrentProperty, User, onclause=CurrentProperty.user_id == User.id))
        .where(CurrentProperty.property_name.in_(EXPORTED_PROPERTIES))
        .group_by(CurrentProperty.property_name)
    ).fetchall()


def establish_and_return_ldap_connection(host, port, use_ssl, ca_certs_file,
                                         ca_certs_data, bind_dn, bind_pw):
    tls = None
    if ca_certs_file or ca_certs_data:
        tls = ldap3.Tls(ca_certs_file=ca_certs_file,
                        ca_certs_data=ca_certs_data, validate=ssl.CERT_REQUIRED)
    server = ldap3.Server(host=host, port=port, use_ssl=use_ssl, tls=tls)
    return ldap3.Connection(server, user=bind_dn, password=bind_pw, auto_bind=True)


def fetch_ldap_entries(connection, base_dn, search_filter=None, attributes=ldap3.ALL_ATTRIBUTES):
    success = connection.search(search_base=base_dn,
                                search_filter=search_filter,
                                attributes=attributes)
    if not success:
        logger.warning("LDAP search not successful.  Result: %s", connection.result)
        return []

    return [r for r in connection.response if r['dn'] != base_dn]


def fetch_current_ldap_users(connection, base_dn):
    return fetch_ldap_entries(connection, base_dn,
                              search_filter='(objectclass=inetOrgPerson)',
                              attributes=[ldap3.ALL_ATTRIBUTES, 'pwdAccountLockedTime'])


def fetch_current_ldap_groups(connection, base_dn):
    return fetch_ldap_entries(connection, base_dn, search_filter='(objectclass=groupOfMembers)')


def fetch_current_ldap_properties(connection, base_dn):
    return fetch_ldap_entries(connection, base_dn, search_filter='(objectclass=groupOfMembers)')


def fake_connection():
    server = ldap3.Server('mocked')
    connection = ldap3.Connection(server, client_strategy=ldap3.MOCK_SYNC)
    connection.open()
    return connection


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
    action_types = Counter((type(a).__name__ for a in exporter.actions))
    logger.info("Compiled %s actions (%s)", len(exporter.actions),
                ", ".join("{}: {}".format(type_, count)
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
        return os.environ['PYCROFT_LDAP_{}'.format(key.upper())]
    except KeyError as e:
        if key not in defaults:
            print("defaults:", defaults)
            raise ValueError("Missing configuration key {}".format(key)) from e
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
