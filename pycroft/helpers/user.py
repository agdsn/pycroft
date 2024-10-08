# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.helpers.user
~~~~~~~~~~~~~~~~~~~~
"""
import random
import string
import typing as t
from hashlib import sha512

from passlib.apps import ldap_context
from passlib.context import CryptContext
from passlib.pwd import genword

crypt_context: CryptContext = ldap_context.copy(
    default="ldap_sha512_crypt",
    deprecated=["ldap_plaintext", "ldap_md5", "ldap_sha1", "ldap_salted_md5",
                "ldap_des_crypt", "ldap_bsdi_crypt", "ldap_md5_crypt"])

clear_password_prefix = '{clear}'


def generate_password(length: int) -> str:
    """Generate a password of a certain length.

    The password is generated as :paramref:`length` independent choices
    of a certain charset.  The charset does not include ambiguous
    characters like ``l``, ``1``, ``0`` and ``O``.

    :param: length
    """
    # without hard to distinguish characters l/1 0/O
    charset = "abcdefghijkmnopqrstuvwxyz!$%&()=.," \
              ":;-_#+23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
    return t.cast(str, genword(length=length, chars=charset))


def hash_password(plaintext_passwd: str) -> str:
    """Generate a :rfc:`2307` complaint hash from given plaintext.

    The passlib CryptContext is configured to generate the very secure
    ldap_sha512_crypt hashes (a crypt extension available since glibc 2.7).
    """
    return t.cast(str, crypt_context.hash(plaintext_passwd))


def cleartext_password(plaintext_passwd: str) -> str:
    """Generate a :rfc:`2307` complaint hash from given plaintext.

    The passlib CryptContext is configured to generate the very secure
    ldap_sha512_crypt hashes (a crypt extension available since glibc 2.7).
    """
    return f"{clear_password_prefix}{plaintext_passwd}"


def verify_password(plaintext_password: str, hash: str) -> bool:
    """Verifies a plain password string against a given password hash.

    It uses a crypt_context to verify :rfc:`2307` hashes.
    """
    try:
        return t.cast(bool, crypt_context.verify(plaintext_password, hash))
    # TypeError is required for user entries not having a hash
    except (ValueError, TypeError):
        return False


def login_hash(login: str) -> bytes:
    """Hashes a login with sha512, as is done in the `User.login_hash` generated column."""
    return sha512(login.encode()).digest()


def generate_random_str(length: int) -> str:
    """
    Generates an aplhanumeric random string

    """
    return ''.join(
        random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
        for _ in range(length)
    )
