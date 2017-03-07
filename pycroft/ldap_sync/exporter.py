import os
from collections import defaultdict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pycroft.model.user import User
from .action import AddAction, DeleteAction, IdleAction, ModifyAction

BASE_DN = ''  #TODO: implement configuration

def dn_from_username(username, base=BASE_DN):
    return "uid={},{}".format(username, base)


class RecordState(object):
    """A Class representing the state of a user record."""
    def __init__(self, current=None, desired=None):
        self.current = current
        self.desired = desired

    def __eq__(self, other):
        try:
            return self.current == other.current and self.desired == other.desired
        except KeyError:
            return False

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
        return cls(dn=record['dn'], attrs=record['attributes'])

    def __sub__(self, other):
        """Return the action needed to transform another record into this one"""
        if other is None:
            return AddAction(record=self)

        if self.dn != getattr(other, 'dn', object()):
            raise TypeError("Cannot compute difference to record with different dn")

        if self == other:
            return IdleAction(self)

        return ModifyAction.from_two_records(desired_record=self, current_record=other)

    def __rsub__(self, other):
        if other is None:
            return DeleteAction(record=self)
        return NotImplemented

    def __eq__(self, other):
        try:
            return self.dn == other.dn and self.attrs == other.attrs
        except KeyError:
            return False

    def __repr__(self):
        return "<{} dn={}>".format(type(self).__name__, self.dn)

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
