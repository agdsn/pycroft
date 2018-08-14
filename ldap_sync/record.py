# -*- coding: utf-8 -*-
from ldap3.utils.conv import escape_filter_chars

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

    A record represents the user which is to be synced to the LDAP,
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
        attrs = {k: v for k, v in attrs.items() if k in self.ENFORCED_KEYS}
        for key in self.ENFORCED_KEYS:
            attrs.setdefault(key, [])
        # escape_filter_chars is idempotent ⇒ no double escaping
        self.attrs = {key: [_maybe_escape_filter_chars(x)
                            for x in _canonicalize_to_list(val)]
                      for key, val in attrs.items()}

    ENFORCED_KEYS = frozenset(['mail', 'sn', 'cn', 'loginShell', 'gecos', 'userPassword',
                               'homeDirectory', 'gidNumber', 'uidNumber', 'uid'])
    LDAP_LOGIN_ENABLED_PROPERTY = 'ldap_login_enabled'
    PWD_POLICY_BLOCKED = "login_disabled"

    @classmethod
    def from_db_user(cls, user, base_dn):
        dn = dn_from_username(user.login, base=base_dn)
        if user.unix_account == None:
            raise ValueError("User object must have a UnixAccount")

        user_is_blocked = not user.has_property(cls.LDAP_LOGIN_ENABLED_PROPERTY)
        passwd_hash = "!" if user_is_blocked else "" + user.passwd_hash

        attributes = {
            # REQ – required, MAY – optional, SV – single valued
            'uid': user.login,  # REQ by posixAccount, shadowAccount
            'uidNumber': user.unix_account.uid,  # SV, REQ by posixAccount
            'gidNumber': user.unix_account.gid,  # SV, REQ by posixAccount
            'homeDirectory': user.unix_account.home_directory,  # SV, REQ by posixAccount
            'userPassword': passwd_hash,  # MAY by posixAccount, shadowAccount
            'gecos': user.name,  # SV, MAY by posixAccount
            'loginShell': user.unix_account.login_shell,  # SV, MAY by posixAccount
            'cn': user.name,  # REQ by posixAccount, inetOrgPerson(person)
            'sn': user.name,  # REQ by inetOrgPerson(person), here same as cn
            'mail': user.email,  # MAY by inetOrgPerson
        }
        if user_is_blocked:
            attributes['pwdPolicySubEntry'] = cls.PWD_POLICY_BLOCKED
        return cls(dn=dn, attrs=attributes)

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


class RecordState(object):
    """A Class representing the state (current, desired) of a user
    record.

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
