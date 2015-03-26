# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from passlib.hash import (
    ldap_des_crypt, ldap_sha512_crypt, ldap_md5, ldap_salted_sha1)
from pycroft.helpers.user import (
    generate_password, hash_password, verify_password)


class TestPasswordGeneration(unittest.TestCase):
    def test_length(self):
        """Assert that generated passwords are of correct length"""
        for length in range(2, 30):
            self.assertEqual(len(generate_password(length)), length)

    def test_uniqueness(self):
        """Assert that new passwords are generated for each invocation"""
        passwords = tuple(generate_password(8) for i in range(100))
        self.assertEqual(len(passwords), len(set(passwords)))


class TestHashing(unittest.TestCase):
    def test_salt_generation(self):
        """The same password should be encrypted differently for each
        invocation."""
        pw = generate_password(8)
        hashes = tuple(hash_password(pw) for i in range(10))
        self.assertEqual(len(hashes), len(set(hashes)),)

    def test_hash_verification(self):
        """Test that all currently employed password schemes are supported by
        the verification function."""
        pw = generate_password(8)
        for hash_method in (ldap_des_crypt, ldap_sha512_crypt, ldap_md5,
                            ldap_salted_sha1):
            encrypted = hash_method.encrypt(pw)
            self.assertTrue(verify_password(pw, encrypted),
                            "{}: '{}' should verify '{}'"
                            .format(hash_method.name, encrypted, pw))

    def test_hash_type(self):
        """Assert that the password scheme used for new passwords is
        ldap_sha512_crypt."""
        expected_hash_method = ldap_sha512_crypt
        for pw in (generate_password(8) for i in range(100)):
            encrypted = hash_password(pw)
            self.assertTrue(expected_hash_method.identify(encrypted),
                            "Expected hashes for method {}, got: {}"
                            .format(expected_hash_method.name, encrypted))
