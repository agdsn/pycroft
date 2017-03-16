# -*- coding: utf-8; -*-
from __future__ import print_function

import logging
import os
from collections import Counter, defaultdict

import ldap3
from sqlalchemy import create_engine, func
from sqlalchemy.orm import scoped_session, sessionmaker

from pycroft.model.user import User
from pycroft.model.session import set_scoped_session, session as global_session
from .record import Record, RecordState, config

logger = logging.getLogger('ldap_sync')


class LdapExporter(object):
    """The ldap Exporter

    Usage:

        >>> from pycroft.ldap_sync.record import Record
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
    def from_orm_objects_and_ldap_result(cls, current, desired):
        """Construct an exporter instance with non-raw parameters

        :param cls:
        :param current: An iterable of records as returned by
            ldapsearch
        :param desired: An iterable of sqlalchemy objects
        """
        return cls((cls.Record.from_ldap_record(x) for x in current),
                   (cls.Record.from_db_user(x) for x in desired))

    def compile_actions(self):
        """Consolidate current and desired records into necessary actions"""
        if self.actions:
            raise RuntimeError("Actions can only be compiled once")
        for state in self.states_dict.values():
            self.actions.append(state.desired - state.current)

    def execute_all(self, *a, **kw):
        for action in self.actions:
            action.execute(*a, **kw)


def establish_and_return_session():
    try:
        connection_string = os.environ['PYCROFT_DB_URI']
    except KeyError:
        print("Please give the database URI in `PYCROFT_DB_URI`")
        exit(1)
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


def establish_and_return_ldap_connection():
    server = ldap3.Server('host')
    return ldap3.Connection(server, user='cn=admin', password='admin_pw')


def fetch_current_ldap_users(connection):
    success = connection.search(search_base='ou=users,dc=agdsn,dc=de',
                                search_filter='(objectclass=*)',
                                attributes=ldap3.ALL_ATTRIBUTES)
    if not success:
        return []

    return connection.response


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


def sync_all(db_users, ldap_users, connection):
    exporter = LdapExporter.from_orm_objects_and_ldap_result(current=ldap_users,
                                                             desired=db_users)
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


def main():
    add_stdout_logging(logger)
    db_users = fetch_users_to_sync(session=establish_and_return_session())
    logger.info("Fetched %s database users", len(db_users))

    #TODO: configure it to use a real connection
    # connection = establish_and_return_ldap_connection()
    connection = fake_connection()

    ldap_users = fetch_current_ldap_users(connection)
    logger.info("Fetched %s ldap users", len(ldap_users))

    config.BASE_DN = 'ou=users,dc=agdsn,dc=de'
    logger.debug("BASE_DN set to %s", config.BASE_DN)

    sync_all(db_users, ldap_users, connection)


if __name__ == '__main__':
    main()
