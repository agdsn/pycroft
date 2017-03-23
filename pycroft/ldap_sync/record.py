# -*- coding: utf-8 -*-
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


class Record(object):
    def __init__(self, dn, attrs):
        """Create a new record with a dn and certain attributes.

        :param str dn: The DN of the record
        :param dict attrs: The attributes of the record.  Every value
            will be canonicalized to a list to allow for a senseful
            comparison between two records.  Additionally, the keys
            are fixed to a certain set.
        """
        self.dn = dn
        attrs = {k: v for k, v in attrs.items() if k in self.ENFORCED_KEYS}
        for key in self.ENFORCED_KEYS:
            attrs.setdefault(key, [])
        self.attrs = {key: _canonicalize_to_list(val) for key, val in attrs.items()}

    ENFORCED_KEYS = frozenset(['mail', 'sn', 'cn', 'loginShell', 'gecos', 'userPassword',
                               'homeDirectory', 'gidNumber', 'uidNumber', 'uid'])

    @classmethod
    def from_db_user(cls, user, base_dn):
        dn = dn_from_username(user.login, base=base_dn)
        if user.unix_account == None:
            raise ValueError("User object must have a UnixAccount")

        attributes = {
            # REQ – required, MAY – optional, SV – single valued
            'uid': user.login,  # REQ by posixAccount, shadowAccount
            'uidNumber': user.unix_account.uid,  # SV, REQ by posixAccount
            'gidNumber': user.unix_account.gid,  # SV, REQ by posixAccount
            'homeDirectory': user.unix_account.home_directory,  # SV, REQ by posixAccount
            'userPassword': user.passwd_hash,  # MAY by posixAccount, shadowAccount
            'gecos': user.name,  # SV, MAY by posixAccount
            'loginShell': user.unix_account.login_shell,  # SV, MAY by posixAccount
            'cn': user.name,  # REQ by posixAccount, inetOrgPerson(person)
            'sn': user.name,  # REQ by inetOrgPerson(person), here same as cn
            'mail': user.email,  # MAY by inetOrgPerson
        }
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
