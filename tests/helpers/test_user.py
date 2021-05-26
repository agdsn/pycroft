# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest

import pytest
from passlib.hash import ldap_des_crypt, ldap_sha512_crypt, ldap_md5, ldap_salted_sha1
from pycroft.helpers.user import generate_password, hash_password, verify_password


class TestPasswordGeneration:
    @pytest.mark.parametrize('length', list(range(2, 30)))
    def test_length(self, length: int):
        """Assert that generated passwords are of correct length"""
        assert len(generate_password(length)) == length

    def test_uniqueness(self):
        """Assert that new passwords are generated for each invocation"""
        passwords = tuple(generate_password(8) for i in range(100))
        assert len(passwords) == len(set(passwords))


class TestHashing:
    @pytest.fixture(scope='class')
    def pw(self) -> str:
        return generate_password(8)

    @pytest.mark.slow
    def test_salt_generation(self, pw):
        """The same password should be encrypted differently for each
        invocation."""
        hashes = tuple(hash_password(pw) for i in range(10))
        assert len(hashes) == len(set(hashes))

    @pytest.mark.parametrize('hash_method', [
        ldap_des_crypt, ldap_sha512_crypt, ldap_md5, ldap_salted_sha1
    ])
    def test_hash_verification(self, pw, hash_method):
        """Test that all currently employed password schemes are supported by
        the verification function."""
        encrypted = hash_method.hash(pw)
        assert verify_password(pw, encrypted), \
            f"{hash_method.name}: '{encrypted}' should verify '{pw}'"

    @pytest.mark.parametrize('random_pw', (generate_password(8) for i in range(10)))
    def test_hash_type(self, random_pw):
        """Assert that the password scheme used for new passwords is
        ldap_sha512_crypt."""
        expected_hash_method = ldap_sha512_crypt
        encrypted = hash_password(random_pw)
        assert expected_hash_method.identify(encrypted), \
            f"Expected hashes for method {expected_hash_method.name}, got: {encrypted}"
