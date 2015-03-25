# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from passlib.apps import ldap_context
import passlib.utils

ldap_context = ldap_context.copy(default="ldap_sha512_crypt")


def generate_password(length):
    charset = "abcdefghijklmnopqrstuvwxyz!$%&()=.," \
              ":;-_#+1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return passlib.utils.generate_password(length, charset)


def hash_password(plaintext_passwd):
    """Use a ldap_context to generate a RFC 2307 from given plaintext.

    The ldap_context is configured to generate the very secure ldap_sha512_crypt
    hashes (a crypt extension available since glibc 2.7).
    """
    return ldap_context.encrypt(plaintext_passwd)


def verify_password(plaintext_password, hash):
    """Verifies a plain password string against a given password hash.

    It uses a ldap_context to verify RFC 2307 hashes.
    """
    try:
        return ldap_context.verify(plaintext_password, hash)
    except ValueError:
        return False
