#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
ldap_sync.conversion
~~~~~~~~~~~~~~~~~~~~
Converts DB information to :class:`record.Record` instances.
"""
from __future__ import annotations

import typing

from ldap3.utils.dn import safe_dn

from ldap_sync.concepts.record import UserRecord, GroupRecord
from ldap_sync.types import DN, Attributes, LdapRecord
from pycroft.model.user import User


def db_user_to_record(
    user: User, base_dn: DN, should_be_blocked: bool = False
) -> UserRecord:
    assert user.login is not None, "user must be persisted and have a login!"
    assert user.name is not None, "user must be persisted and have a name!"

    dn = dn_from_username(user.login, base=base_dn)
    if user.unix_account is None:
        raise ValueError("User object must have a UnixAccount")

    # Disabling the password is just a safety measure on top of the
    # pwdLockout mechanism
    pwd_hash_prefix = "!" if should_be_blocked else ""
    passwd_hash = pwd_hash_prefix + user.passwd_hash if user.passwd_hash else None

    attributes: Attributes = {
        # REQ – required, MAY – optional, SV – single valued
        "objectClass": UserRecord.LDAP_OBJECTCLASSES,
        "uid": user.login,  # REQ by posixAccount, shadowAccount
        "uidNumber": user.unix_account.uid,  # SV, REQ by posixAccount
        "gidNumber": user.unix_account.gid,  # SV, REQ by posixAccount
        "homeDirectory": user.unix_account.home_directory,  # SV, REQ by posixAccount
        "userPassword": passwd_hash,  # MAY by posixAccount, shadowAccount
        "gecos": user.name.encode(
            "ascii", "replace"
        ),  # SV, MAY by posixAccount, IA5String
        "loginShell": user.unix_account.login_shell,  # SV, MAY by posixAccount
        "cn": user.name,  # REQ by posixAccount, inetOrgPerson(person)
        "sn": user.name,  # REQ by inetOrgPerson(person), here same as cn
        "mail": user.email if user.email_forwarded else None,  # MAY by inetOrgPerson
    }
    if should_be_blocked:
        # See man slapo-ppolicy
        # A 000001010000Z value means that the account has been locked permanently,
        # and that only a password administrator can unlock the account.
        attributes[
            "pwdAccountLockedTime"
        ] = "000001010000Z"  # 1.3.6.1.4.1.42.2.27.8.1.17
        # See man shadow
        # The date of expiration of the account, expressed as the number of days since Jan 1, 1970.
        # The value 0 should not be used as it is interpreted as either
        # an account with no expiration, or as an expiration on Jan 1, 1970.
        attributes["shadowExpire"] = 1
    else:
        attributes |= {
            "pwdAccountLockedTime": [],
            "shadowExpire": [],
        }
    UserRecord._validate_attributes(attributes)
    return UserRecord(dn=dn, attrs=attributes)


def db_group_to_record(
    name: str, members: typing.Iterable[str], base_dn: DN, user_base_dn: DN
) -> GroupRecord:
    dn = dn_from_cn(name, base=base_dn)
    members_dn: list[str] = [
        dn_from_username(member, user_base_dn) for member in members
    ]

    attributes: Attributes = {
        # REQ – required, MAY – optional, SV – single valued
        "objectClass": GroupRecord.LDAP_OBJECTCLASSES,
        "cn": name,  # REQ by groupOfMembers
        "member": members_dn,  # MAY by groupOfMembers
    }
    GroupRecord._validate_attributes(attributes)
    return GroupRecord(dn=dn, attrs=attributes)


def dn_from_username(username: str, base: DN) -> DN:
    return DN(safe_dn([f"uid={username}", base]))


def dn_from_cn(name: str, base: DN) -> DN:
    return DN(safe_dn([f"cn={name}", base]))


def ldap_user_to_record(record: LdapRecord) -> UserRecord:
    return UserRecord(dn=record["dn"], attrs=record["attributes"])


def ldap_group_to_record(record: LdapRecord) -> GroupRecord:
    return GroupRecord(dn=record["dn"], attrs=record["attributes"])
