# -*- coding: utf-8; -*-
from __future__ import print_function

import argparse
import logging
import os
import sys
from collections import Counter, defaultdict, namedtuple

import ldap3
from sqlalchemy import create_engine, func
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model.user import User
from pycroft.model.session import set_scoped_session, session as global_session
from .record import Record, RecordState

logger = logging.getLogger('ldap_sync')


class LdapExporter(object):
    """The ldap Exporter

    Usage:

        >>> from ldap_sync.record import Record
        >>> record = Record(dn='cn=admin,ou=users,dc=agdsn,dc=de', attrs={})
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
    RecordState = RecordState
    Record = Record

    def __init__(self, current, desired):
        self.states_dict = defaultdict(self.RecordState)
        for record in current:
            self.states_dict[record.dn].current = record
        for record in desired:
            self.states_dict[record.dn].desired = record
        self.actions = []

    @classmethod
    def from_orm_objects_and_ldap_result(cls, current, desired, base_dn):
        """Construct an exporter instance with non-raw parameters

        :param cls:
        :param current: An iterable of records as returned by
            ldapsearch
        :param desired: An iterable of sqlalchemy objects
        """
        return cls((cls.Record.from_ldap_record(x) for x in current),
                   (cls.Record.from_db_user(x, base_dn) for x in desired))

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


def fetch_users_to_sync(session):
    """Fetch the users who should be synced

    :param session: The SQLAlchemy session to use

    :returns: A list of :py:cls:`User` objects having the property
              'mail' having a unix_account.
    """
    count_mail_but_not_account = (
        session.query(func.count(User.id))
        .filter(User.has_property('mail'),
                User.unix_account == None)
        .scalar()
    )
    logger.warning("%s users have the 'mail' property but not a unix_account",
                   count_mail_but_not_account)

    return User.q.filter(User.has_property('mail'), User.unix_account != None).all()


def establish_and_return_ldap_connection(host, port, bind_dn, bind_pw):
    server = ldap3.Server(host=host, port=port)
    return ldap3.Connection(server, user=bind_dn, password=bind_pw, auto_bind=True)


def fetch_current_ldap_users(connection, base_dn):
    success = connection.search(search_base=base_dn,
                                search_filter='(objectclass=*)',
                                attributes=ldap3.ALL_ATTRIBUTES)
    if not success:
        logger.warning("LDAP search not successful.  Result: %s", connection.result)
        return []

    return [r for r in connection.response if r['dn'] != base_dn]


def fake_connection():
    server = ldap3.Server('mocked')
    connection = ldap3.Connection(server, client_strategy=ldap3.MOCK_SYNC)
    connection.open()
    return connection


def add_stdout_logging(logger):
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(levelname)s %(asctime)s %(name)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def sync_all(db_users, ldap_users, connection, base_dn):
    exporter = LdapExporter.from_orm_objects_and_ldap_result(current=ldap_users,
                                                             desired=db_users,
                                                             base_dn=base_dn)
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
    ['host', 'port', 'bind_dn', 'bind_pw', 'base_dn', 'db_uri']
)


def get_config():
    config_dict = {
        # e.g. 'host': 'PYCROFT_LDAP_HOST'
        key: os.environ['PYCROFT_LDAP_{}'.format(key.upper())]
        for key in _sync_config._fields if key != 'db_uri'
    }
    config_dict['port'] = int(config_dict['port'])
    config_dict['db_uri'] = os.environ['PYCROFT_DB_URI']
    config = _sync_config(**config_dict)

    return config


def get_config_or_exit():
    try:
        return get_config()
    except KeyError as exc:
        logger.critical("%s not set, quitting", exc.args[0])
        exit()


def main():
    logger.info("Starting the production sync. See --help for other options.")
    config = get_config_or_exit()

    db_users = fetch_users_to_sync(
        session=establish_and_return_session(config.db_uri)
    )
    logger.info("Fetched %s database users", len(db_users))

    connection = establish_and_return_ldap_connection(
        host=config.host,
        port=config.port,
        bind_dn=config.bind_dn,
        bind_pw=config.bind_pw,
    )

    ldap_users = fetch_current_ldap_users(connection, base_dn=config.base_dn)
    logger.info("Fetched %s ldap users", len(ldap_users))

    sync_all(db_users, ldap_users, connection, base_dn=config.base_dn)


def main_fake_ldap():
    logger.info("Starting sync using a mocked LDAP backend. See --help for other options.")
    try:
        db_uri = os.environ['PYCROFT_DB_URI']
    except KeyError:
        logger.critical('PYCROFT_DB_URI not set')
        exit()

    db_users = fetch_users_to_sync(
        session=establish_and_return_session(db_uri)
    )
    logger.info("Fetched %s database users", len(db_users))

    connection = fake_connection()
    BASE_DN = 'ou=users,dc=agdsn,dc=de'
    logger.debug("BASE_DN set to %s", BASE_DN)

    ldap_users = fetch_current_ldap_users(connection, base_dn=config.BASE_DN)
    logger.info("Fetched %s ldap users", len(ldap_users))

    sync_all(db_users, ldap_users, connection, base_dn=BASE_DN)


if __name__ == '__main__':
    add_stdout_logging(logger)
    parser = argparse.ArgumentParser(description="Pycroft ldap syncer")
    parser.add_argument('--fake', dest='fake', action='store_true',
                        help="Use a mocked LDAP backend")
    parser.set_defaults(fake=False)
    args = parser.parse_args()

    if args.fake:
        main_fake_ldap()
    else:
        main()
