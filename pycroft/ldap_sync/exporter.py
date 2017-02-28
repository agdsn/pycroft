import os
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pycroft.model.user import User

BASE_DN = ''  #TODO: implement configuration

def dn_from_username(username, base=BASE_DN):
    return "uid={},{}".format(username, base)


class RecordState(object):
    """A Class representing the state of a user record."""
    def __init__(self, current=None, desired=None):
        self.current = current
        self.desired = desired

    def __repr__(self):
        set_attributes = []
        if self.current:
            set_attributes.append('current')
        if self.desired:
            set_attributes.append('desired')
        attrs_string = " " + " ".join(set_attributes) if set_attributes else ''
        return "<{cls}{attrs}>".format(cls=type(self).__name__, attrs=attrs_string)


class Record(object):
    BASE_DN = BASE_DN

    def __init__(self, dn, attrs):
        """Create a new record with a dn and certain attributes."""
        self.dn = dn
        self.attrs = attrs

    @classmethod
    def from_db_user(cls, user):
        dn = dn_from_username(user.login)
        attributes = {}  #TODO: Fill
        return cls(dn=dn, attrs=attributes)

    @classmethod
    def from_ldap_record(cls, record):
        dn = dn_from_username(record.uid)
        attributes = {}  #TODO: Fill
        return cls(dn=dn, attrs=attributes)


class LdapExporter(object):
    RecordState = RecordState
    Record = Record

    def __init__(self, current, desired):
        self.state = defaultdict(self.RecordState)
        self.populate_current(current)
        self.populate_desired(desired)

    def populate_current(self, current_objects):
        for obj in current_objects:
            record = self.Record.from_ldap_record(obj)
            self.state[record.dn].current = record

    def populate_desired(self, desired_objects):
        for obj in desired_objects:
            record = self.Record.from_db_user(obj)
            self.state[record.dn].desired = record

    def consolidate_state_to_action(self, state):
        """Turn a RecordState into an Action (add/del/mod/idle)

        TODO: Implement (perhaps in Record.__sub__ s.t.
        ``action = desired - current``)
        """
        raise NotImplementedError


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
