# -*- coding: utf-8 -*-
import abc

from ldap3.utils.conv import escape_filter_chars

from pycroft.model.user import User
from .action import AddAction, DeleteAction, IdleAction, ModifyAction


def dn_from_username(username, base):
    return "uid={},{}".format(username, base)


def _canonicalize_to_list(value):
    """Canonicalize a value to a list.

    If value is a list, return it.  If it is None or an empty string,
    return an empty list.  Else, return value.
    """
    if isinstance(value, list):
        return value
    if value == '' or value is None:
        return []
    return [value]


def _maybe_escape_filter_chars(value):
    """Escape and return according to RFC04515 if type is string-like.

    Else, return the unchanged object.
    """
    if isinstance(value, type(b'')) or isinstance(value, type(u'')):
        return escape_filter_chars(value)
    return value


class Record(object):
    """Create a new record with a dn and certain attributes.

    A record represents an entry which is to be synced to the LDAP,
    and consists of a dn and relevant attributes.  Constructors are
    provided for SQLAlchemy ORM objects as well as entries of an ldap
    search response.

    :param str dn: The DN of the record
    :param dict attrs: The attributes of the record.  Every value will
        be canonicalized to a list to allow for a senseful comparison
        between two records, as well as escaped according to RFC04515.
        Additionally, the keys are fixed to a certain set.
    """
    def __init__(self, dn, attrs):
        self.dn = dn
        attrs = {k: v for k, v in attrs.items() if k in self.get_synced_attributes()}
        for key in self.get_synced_attributes():
            attrs.setdefault(key, [])
        # escape_filter_chars is idempotent ⇒ no double escaping
        self.attrs = {key: [_maybe_escape_filter_chars(x)
                            for x in _canonicalize_to_list(val)]
                      for key, val in attrs.items()}

    @classmethod
    @abc.abstractmethod
    def get_synced_attributes(cls):
        """Returns the attributes to be synced."""
        return

    @classmethod
    def from_ldap_record(cls, record):
        return cls(dn=record['dn'], attrs=record['attributes'])

    def remove_empty_attributes(self):
        self.attrs = {key: val for key, val in self.attrs.items() if val}

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
        except AttributeError:
            return False

    def __repr__(self):
        return "<{} dn={}>".format(type(self).__name__, self.dn)


class UserRecord(Record):
    """Create a new user record with a dn and certain attributes.
    """
    def __init__(self, dn, attrs):
        super().__init__(dn, attrs)

    SYNCED_ATTRIBUTES = frozenset([
        'objectClass',
        'mail', 'sn', 'cn', 'loginShell', 'gecos', 'userPassword',
        'homeDirectory', 'gidNumber', 'uidNumber', 'uid',
        'pwdAccountLockedTime', 'shadowExpire'
    ])
    LDAP_OBJECTCLASSES = ['top', 'inetOrgPerson', 'posixAccount', 'shadowAccount']
    LDAP_LOGIN_ENABLED_PROPERTY = 'ldap_login_enabled'
    PWD_POLICY_BLOCKED = "login_disabled"

    @classmethod
    def get_synced_attributes(cls):
        return cls.SYNCED_ATTRIBUTES

    @classmethod
    def from_db_user(cls, user, base_dn, should_be_blocked=False):
        # type: (User, str, bool) -> Record
        dn = dn_from_username(user.login, base=base_dn)
        if user.unix_account is None:
            raise ValueError("User object must have a UnixAccount")

        # Disabling the password is just a safety measure on top of the
        # pwdLockout mechanism
        pwd_hash_prefix = "!" if should_be_blocked else ""
        passwd_hash = pwd_hash_prefix + user.passwd_hash if user.passwd_hash else None

        attributes = {
            # REQ – required, MAY – optional, SV – single valued
            'objectClass': cls.LDAP_OBJECTCLASSES,
            'uid': user.login,  # REQ by posixAccount, shadowAccount
            'uidNumber': user.unix_account.uid,  # SV, REQ by posixAccount
            'gidNumber': user.unix_account.gid,  # SV, REQ by posixAccount
            'homeDirectory': user.unix_account.home_directory,  # SV, REQ by posixAccount
            'userPassword': passwd_hash,  # MAY by posixAccount, shadowAccount
            'gecos': user.name.encode("ascii","replace"),  # SV, MAY by posixAccount, IA5String
            'loginShell': user.unix_account.login_shell,  # SV, MAY by posixAccount
            'cn': user.name,  # REQ by posixAccount, inetOrgPerson(person)
            'sn': user.name,  # REQ by inetOrgPerson(person), here same as cn
            'mail': user.email,  # MAY by inetOrgPerson
        }
        if should_be_blocked:
            # See man slapo-ppolicy
            # A 000001010000Z value means that the account has been locked permanently,
            # and that only a password administrator can unlock the account.
            attributes['pwdAccountLockedTime'] = "000001010000Z"  # 1.3.6.1.4.1.42.2.27.8.1.17
            # See man shadow
            # The date of expiration of the account, expressed as the number of days since Jan 1, 1970.
            # The value 0 should not be used as it is interpreted as either
            # an account with no expiration, or as an expiration on Jan 1, 1970.
            attributes['shadowExpire'] = 1

        # sanity check: did we forget something in `cls.SYNCED_ATTRIBUTES` that
        # we support migrating anyway?
        _missing_attributes = set(attributes.keys()) - cls.SYNCED_ATTRIBUTES
        assert not _missing_attributes, \
            "SYNCED_ATTRIBUTES does not contain attributes {}".format(_missing_attributes)

        return cls(dn=dn, attrs=attributes)

    def __sub__(self, other):
        action = super().__sub__(other)

        # Do not try to delete pwdAccountLockedTime if password is changed,
        # as the ppolicy overlay already takes care of that.
        if isinstance(action, ModifyAction):
            if 'userPassword' in action.modifications and not action.modifications.get(
                    'pwdAccountLockedTime', None):
                action.modifications.pop('pwdAccountLockedTime', None)

        return action


class RecordState(object):
    """A Class representing the state (current, desired) of a record.

    This class is essentially a duple consisting of a current and
    desired record to represent the difference.

    :param Record current: The current record
    :param Record desired: The desired record
    """
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
