# -*- coding: utf-8 -*-
"""
    pycroft.helpers.user_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by AG DSN.
"""

import random
from crypt import crypt
from passlib.apps import ldap_context

# ToDo: evaluate if we need "ldap_sha1_crypt" here for cpmpatibility
ldap_context = ldap_context.replace(default="ldap_salted_sha1")


def generate_password(length):
    allowed_letters = "abcdefghijklmnopqrstuvwxyz!$%&()=.,"\
                     ":;-_#+1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "".join(random.sample(allowed_letters, length))


def generate_crypt_salt(salt_length):
    allowed_letters = [chr(x) for x in
                       range(ord("a"), ord("z") + 1) +
                       range(ord("A"), ord("Z") + 1) +
                       range(ord("0"), ord("9") + 1)] + \
                      [".", "/"]
    return "".join(random.sample(allowed_letters, salt_length))


def hash_password(plaintext_passwd):
    """Use a ldap_context to generate a RFC 2307 from given plaintext.

    The ldap_context is preconfigured to generate ldap_salted_sha1
    hashes (prefixed with {SSHA}).
    """
    return ldap_context.encrypt(plaintext_passwd)


def verify_password(plaintext_password, hash):
    """Verifies a plain password string agailst a given password hash.

    It uses a ldap_context to verify RFC 2307 hashes including the GNU
    {crypt} extension. If the passord is a basic 2-byte-salted hash
    given grom old unix crypt() the ldap_context will fail. For this we
    try to crypt() the given plaintext using the first two bytes of the
    given hash als salt and compare the two hashes.
    """
    try:
        result = ldap_context.verify(plaintext_password, hash)
        if result:
            return result
    except ValueError:
        pass
    if hash.startswith("{crypt}") and len(hash) > 9:
        real_hash = hash[7:]
        salt = hash[7:9]
        crypted = crypt(plaintext_password, salt)
        return crypted == real_hash
    return False
