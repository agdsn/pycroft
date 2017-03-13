# -*- coding: utf-8; -*-
import os
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pycroft.model.user import User
from .record import Record, RecordState


class LdapExporter(object):
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

    def execute_all(self):
        for action in self.actions:
            #TODO: Do we need a connection? perhaps introduce it as a parameter
            action.execute()


def init_db_session():
    #TODO: implement+test
    try:
        connection_string = os.environ['PYCROFT_DB_URI']
    except KeyError:
        print("Please give the database URI in `PYCROFT_DB_URI`")
        exit(1)
    engine = create_engine(connection_string)
    session = sessionmaker(bind=engine)
    return session


def iter_db_users_to_sync(session):
    #TODO: return only objects which have an active connection
    return session.query(User).all()


def init_ldap_connection():
    #TODO: implement
    connection = None
    # server = ldap3.Server()
    # connection = ldap3.Connection(server)
    return connection


def iter_current_ldap_users(connection):
    #TODO: call search
    # connection.search()
    return []


def main():
    #TODO: would a cm be better? we only need one query and need not leave the
    #session open
    session = init_db_session()
    db_users = iter_db_users_to_sync(session)
    #TODO: fetch db objects
    # users = User.filter_by(<has_connection?>).all()
    connection = init_ldap_connection()
    ldap_users = iter_current_ldap_users(connection)

    #TODO: init ldap
    #TODO: fetch ldap objects

    #TODO: call registry
    exporter = LdapExporter(current=db_users, desired=ldap_users)
    # exporter.compile_actions()
    # exporter.execute_all()


if __name__ == '__main__':
    main()
