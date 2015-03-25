# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from passlib.apps import ldap_context
import passlib.utils

# ToDo: evaluate if we need "ldap_sha1_crypt" here for cpmpatibility
ldap_context = ldap_context.replace(default="ldap_salted_sha1")


def generate_password(length):
    charset = "abcdefghijklmnopqrstuvwxyz!$%&()=.," \
              ":;-_#+1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return passlib.utils.generate_password(length, charset)


def hash_password(plaintext_passwd):
    """Use a ldap_context to generate a RFC 2307 from given plaintext.

    The ldap_context is preconfigured to generate ldap_salted_sha1
    hashes (prefixed with {SSHA}).
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
