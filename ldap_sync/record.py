from __future__ import annotations
import abc
import dataclasses
import typing

from ldap3.utils.conv import escape_filter_chars
from ldap3.utils.dn import safe_dn

from pycroft.model.user import User
from .types import LdapRecord, Attributes, NormalizedAttributes


def dn_from_username(username: str, base: str) -> str:
    return safe_dn([f"uid={username}", base])


def dn_from_cn(name: str, base: str) -> str:
    return safe_dn([f"cn={name}", base])


T = typing.TypeVar("T")


def _canonicalize_to_list(value: T | list[T]) -> list[T]:
    """Canonicalize a value to a list.

    If value is a list, return it.  If it is None or an empty string,
    return an empty list.  Else, return value.
    """
    if isinstance(value, list):
        return list(value)
    if value == '' or value is None:
        return []
    return [value]


# the “true” type is not expressible with mypy: it's the overload
# bytes | str -> str
# T -> T
# …but mypy rejects this because we have an argument overlap with incompatible return types.
def _maybe_escape_filter_chars(value: T) -> T | str:
    """Escape and return according to RFC04515 if type is string-like.

    Else, return the unchanged object.
    """
    if isinstance(value, bytes) or isinstance(value, str):
        return escape_filter_chars(value)
    return value


# TODO: replace with the py3.11 Self type
TRecord = typing.TypeVar("TRecord", bound="Record")


class Record(abc.ABC):
    """Create a new record with a dn and certain attributes.

    A record represents an entry which is to be synced to the LDAP,
    and consists of a dn and relevant attributes.  Constructors are
    provided for SQLAlchemy ORM objects as well as entries of an ldap
    search response.

    :param dn: The DN of the record
    :param attrs: The attributes of the record.  Every value will
        be canonicalized to a list to allow for a senseful comparison
        between two records, as well as escaped according to RFC04515.
        Additionally, the keys are fixed to a certain set.
    """

    dn: str
    attrs: NormalizedAttributes

    def __init__(self, dn: str, attrs: Attributes) -> None:
        self.dn = dn
        attrs = {k: v for k, v in attrs.items() if k in self.get_synced_attributes()}
        for key in self.get_synced_attributes():
            attrs.setdefault(key, [])
        # escape_filter_chars is idempotent ⇒ no double escaping
        self.attrs = {
            key: [
                _maybe_escape_filter_chars(x)
                for x in typing.cast(list[str], _canonicalize_to_list(val))
            ]
            for key, val in attrs.items()
        }

    @classmethod
    @abc.abstractmethod
    def get_synced_attributes(cls) -> typing.AbstractSet[str]:
        """Returns the attributes to be synced."""
        raise NotImplementedError

    @classmethod
    def from_ldap_record(cls: type[TRecord], record: LdapRecord) -> TRecord:
        return cls(dn=record['dn'], attrs=record['attributes'])

    def remove_empty_attributes(self) -> None:
        self.attrs = {key: val for key, val in self.attrs.items() if val}

    def __eq__(self, other):  # `__eq__` must be total, hence no type restrictions/hints
        try:
            return self.dn == other.dn and self.attrs == other.attrs
        except AttributeError:
            return False

    def __repr__(self):
        return f"<{type(self).__name__} dn={self.dn}>"

    @classmethod
    def _validate_attributes(cls, attributes: Attributes):
        # sanity check: did we forget something in `cls.get_synced_attributes()` that
        # we support migrating anyway?
        _missing_attributes = set(attributes.keys()) - cls.get_synced_attributes()
        assert not _missing_attributes, \
            f"get_synced_attributes() does not contain attributes {_missing_attributes}"


class UserRecord(Record):
    """Create a new user record with a dn and certain attributes.
    """
    def __init__(self, dn: str, attrs: Attributes) -> None:
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
    def from_db_user(
        cls, user: User, base_dn: str, should_be_blocked: bool = False
    ) -> Record:
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
            'mail': user.email if user.email_forwarded else None,  # MAY by inetOrgPerson
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

        cls._validate_attributes(attributes)

        return cls(dn=dn, attrs=attributes)


class GroupRecord(Record):
    """Create a new groupOfMembers record with a dn and certain attributes.
    Used to represent groups and properties.
    """
    def __init__(self, dn, attrs) -> None:
        super().__init__(dn, attrs)

    SYNCED_ATTRIBUTES = frozenset([
        'objectClass', 'cn', 'member'
    ])
    LDAP_OBJECTCLASSES = ['groupOfMembers']

    @classmethod
    def get_synced_attributes(cls):
        return cls.SYNCED_ATTRIBUTES

    @classmethod
    def from_db_group(
        cls, name: str, members: typing.Iterable[str], base_dn: str, user_base_dn: str
    ):
        dn = dn_from_cn(name, base=base_dn)
        members_dn: list[str] = [dn_from_username(member, user_base_dn) for member in members]

        attributes = {
            # REQ – required, MAY – optional, SV – single valued
            'objectClass': cls.LDAP_OBJECTCLASSES,
            'cn': name,  # REQ by groupOfMembers
            'member': members_dn, # MAY by groupOfMembers
        }
        cls._validate_attributes(attributes)

        return cls(dn=dn, attrs=attributes)


@dataclasses.dataclass
class RecordState:
    """A Class representing the state (current, desired) of a record.

    This class is essentially a duple consisting of a current and
    desired record to represent the difference.
    """
    current: Record | None = None
    desired: Record | None = None
