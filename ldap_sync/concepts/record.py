"""
ldap_sync.concepts.record
~~~~~~~~~~~~~~~~~~~~~~~~~
"""
#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from __future__ import annotations

import dataclasses
import typing

from ldap3.utils.conv import escape_filter_chars

from .types import (
    Attributes,
    NormalizedAttributes,
    DN,
    AttributeValues,
)

T = typing.TypeVar("T")


def _canonicalize_to_list(
    value: AttributeValues,
) -> list[str] | list[bytes] | list[int]:
    """Canonicalize a value to a list.

    If value is a list, return it.  If it is None or an empty string,
    return an empty list.  Else, return value.
    """
    if isinstance(value, list):
        return list(value)
    if value == "" or value == b"" or value is None:
        return []
    # str, byte, int – or unknown. But good fallback.
    return [value]  # type: ignore


# the “true” type is not expressible with mypy: it's the overload
# bytes | str -> str
# T -> T
# …but mypy rejects this because we have an argument overlap with incompatible return types.
def _maybe_escape_filter_chars(value: T) -> T | str:
    """Escape and return according to :rfc:`04515` if type is string-like.

    Else, return the unchanged object.
    """
    if isinstance(value, bytes) or isinstance(value, str):
        return typing.cast(str, escape_filter_chars(value))
    return value


# TODO: replace with the py3.11 Self type
TRecord = typing.TypeVar("TRecord", bound="Record")


def escape_and_normalize_attrs(attrs: Attributes) -> NormalizedAttributes:
    return {
        key: [
            _maybe_escape_filter_chars(x)
            for x in typing.cast(list[str], _canonicalize_to_list(val))
        ]
        for key, val in attrs.items()
    }


@dataclasses.dataclass(frozen=True)
class Record:
    """Create a new record with a dn and certain attributes.

    A record represents an entry which is to be synced to the LDAP,
    and consists of a dn and relevant attributes.  Constructors are
    provided for SQLAlchemy ORM objects as well as entries of an ldap
    search response.

    :param dn: The DN of the record
    :param attrs: The attributes of the record.  Every value will
        be canonicalized to a list to allow for a senseful comparison
        between two records, as well as escaped according to :rfc:`04515`.
        Additionally, the keys are fixed to what's given by
        :meth:`get_synced_attributes`.
    """

    dn: DN
    attrs: NormalizedAttributes
    SYNCED_ATTRIBUTES: typing.ClassVar[typing.AbstractSet[str]]

    def __init__(self, dn: DN, attrs: Attributes) -> None:
        object.__setattr__(self, "dn", dn)
        attrs = {k: v for k, v in attrs.items() if k in self.SYNCED_ATTRIBUTES}
        for key in self.SYNCED_ATTRIBUTES:
            attrs.setdefault(key, [])
        # escape_filter_chars is idempotent ⇒ no double escaping
        object.__setattr__(self, "attrs", escape_and_normalize_attrs(attrs))

    def __getitem__(self, item: str) -> typing.Any:
        return self.attrs.__getitem__(item)

    def __init_subclass__(cls, **kwargs: dict[str, typing.Any]) -> None:
        if "SYNCED_ATTRIBUTES" not in cls.__dict__:
            raise TypeError("Subclasses of Record must implement the SYNCED_ATTRIBUTES field")
        super().__init_subclass__(**kwargs)

    # `__eq__` must be total, hence no type restrictions/hints
    def __eq__(self, other: object) -> bool:
        try:
            return self.dn == other.dn and self.attrs == other.attrs  # type: ignore
        except AttributeError:
            return False

    def __repr__(self) -> str:
        return f"<{type(self).__name__} dn={self.dn}>"

    @classmethod
    # we don't care about the values, hence not typing as `Attributes`
    def _validate_attributes(cls, attributes: dict[str, typing.Any]) -> None:
        # sanity check: did we forget something in `cls.SYNCED_ATTRIBUTES` that
        # we support migrating anyway?
        _missing_attrs = cls.SYNCED_ATTRIBUTES - set(attributes.keys())
        assert not _missing_attrs, f"Missing attributes: {_missing_attrs}"
        _superfluous_attrs = set(attributes.keys()) - cls.SYNCED_ATTRIBUTES
        assert not _superfluous_attrs, f"Superfluous attributes: {_superfluous_attrs}"


class UserRecord(Record):
    """Create a new user record with a dn and certain attributes."""

    SYNCED_ATTRIBUTES = frozenset(
        [
            "objectClass",
            "mail",
            "sn",
            "cn",
            "loginShell",
            "gecos",
            "userPassword",
            "homeDirectory",
            "gidNumber",
            "uidNumber",
            "uid",
            "pwdAccountLockedTime",
            "shadowExpire",
        ]
    )
    LDAP_OBJECTCLASSES = ["top", "inetOrgPerson", "posixAccount", "shadowAccount"]
    LDAP_LOGIN_ENABLED_PROPERTY = "ldap_login_enabled"
    PWD_POLICY_BLOCKED = "login_disabled"

    @classmethod
    def get_synced_attributes(cls) -> typing.AbstractSet[str]:
        return cls.SYNCED_ATTRIBUTES


class GroupRecord(Record):
    """Create a new groupOfMembers record with a dn and certain attributes.
    Used to represent groups and properties.
    """

    SYNCED_ATTRIBUTES = frozenset(["objectClass", "cn", "member"])
    LDAP_OBJECTCLASSES = ["groupOfMembers"]


@dataclasses.dataclass
class RecordState:
    """A Class representing the state (current, desired) of a record.

    This class is essentially a duple consisting of a current and
    desired record to represent the difference.
    """

    current: Record | None = None
    desired: Record | None = None
