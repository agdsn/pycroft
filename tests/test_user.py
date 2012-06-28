# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from crypt import crypt
from passlib.hash import ldap_salted_sha1, ldap_md5_crypt, ldap_sha1_crypt

from pycroft.helpers.user_helper import generatePassword, hash_password, verify_password

class TestPasswdHashes(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.hashes = []

        def crypt_pw(pw):
            return "{crypt}" + crypt(pw, generatePassword(2))

        self.methods = {"crypt": crypt_pw,
                        "CRYPT": ldap_sha1_crypt.encrypt,
                        "MD5": ldap_md5_crypt.encrypt,
                        "SSHA": ldap_salted_sha1.encrypt}

        for len in range(4, 20):
            pw = generatePassword(len)
            hash_dict = {"plain": pw}
            for method in self.methods:
                hash_dict[method] = self.methods[method](pw)
            self.hashes.append(hash_dict)
        super(TestPasswdHashes, self).__init__(*args, **kwargs)

    def test_0010_verify(self):
        for pw in self.hashes:
            for method in self.methods:
                self.assertTrue(verify_password(pw["plain"], pw[method]),
                    "%s: '%s' should verify with '%s'" % (
                    method, pw[method], pw["plain"]))
                self.assertFalse(
                    verify_password(pw["plain"], pw[method][len(method) + 2:]))

    def test_0020_generate_hash(self):
        cur_type = "SSHA"
        for pw in self.hashes:
            self.assertNotEqual(hash_password(pw["plain"]), pw[cur_type],
                "Salt should be different!")
            self.assertTrue(
                hash_password(pw["plain"]).startswith("{%s}" % cur_type))

    def test_0030_generate_plain(self):
        pw_list = []
        hash_list = []
        for num in range(1, 500):
            pw = generatePassword(9)
            self.assertEqual(len(pw), 9)
            self.assertFalse(pw in pw_list)
            pw_list.append(pw)
            hash = hash_password(pw)
            self.assertFalse(hash in hash_list)
            hash_list.append(hash)
