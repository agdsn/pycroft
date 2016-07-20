# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from passlib.apps import ldap_context
import passlib.utils

crypt_context = ldap_context.copy(
    default="ldap_sha512_crypt",
    deprecated=["ldap_plaintext", "ldap_md5", "ldap_sha1", "ldap_salted_md5",
                "ldap_des_crypt", "ldap_bsdi_crypt", "ldap_md5_crypt"])


def generate_password(length):
    """Generate a password of a certain length.

    The password is generated as :param:`length` independent choices
    of a certain charset.  The charset does not include ambiguous
    characters like ``l``, ``1``, ``0`` and ``O``.

    :param int length: The length of the password

    :return: The generated password
    :rtype: str
    """
    #without hard to distinguish characters l/1 0/O
    charset = "abcdefghijkmnopqrstuvwxyz!$%&()=.," \
              ":;-_#+23456789ABCDEFGHIJKLMNPQRSTUVWXYZ"
    return passlib.utils.generate_password(length, charset)


def hash_password(plaintext_passwd):
    """Generate a RFC 2307 complaint hash from given plaintext.

    The passlib CryptContext is configured to generate the very secure
    ldap_sha512_crypt hashes (a crypt extension available since glibc 2.7).
    """
    return crypt_context.encrypt(plaintext_passwd)


def verify_password(plaintext_password, hash):
    """Verifies a plain password string against a given password hash.

    It uses a crypt_context to verify RFC 2307 hashes.
    """
    try:
        return crypt_context.verify(plaintext_password, hash)
    # TypeError is required for user entries not having a hash
    except (ValueError, TypeError):
        return False
