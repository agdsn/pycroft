# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import random
import unittest
from passlib.hash import (
    ldap_des_crypt, ldap_sha512_crypt, ldap_md5, ldap_salted_sha1)
from pycroft.helpers.user import (
    generate_password, hash_password, verify_password)


class Test_020_PasswdHashes(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        self.hashes = []

        self.methods = {"crypt": ldap_des_crypt.encrypt,
                        "CRYPT": ldap_sha512_crypt.encrypt,
                        "MD5": ldap_md5.encrypt,
                        "SSHA": ldap_salted_sha1.encrypt}

        for length in range(4,20):
            pw = generate_password(length)
            hash_dict = {"plain": pw}
            for method in self.methods:
                hash_dict[method] = self.methods[method](pw)
            self.hashes.append(hash_dict)
        super(Test_020_PasswdHashes, self).__init__(*args, **kwargs)

    def test_0010_verify(self):
        for pw in self.hashes:
            for method in self.methods:
                self.assertTrue(verify_password(pw["plain"],  pw[method]), "{}: '{}' should verify with '{}'".format(method, pw[method], pw["plain"]))
                self.assertFalse(verify_password(pw["plain"], pw[method][len(method)+2:]))

    def test_0020_generate_hash(self):
        cur_type = "CRYPT"
        for pw in self.hashes:
            self.assertNotEqual(hash_password(pw["plain"]), pw[cur_type], "Salt should be different!")
            self.assertTrue(ldap_sha512_crypt.identify(hash_password(pw["plain"])))

    def test_0030_generate_plain(self):
        pw_list = []
        hash_list = []
        for num in range(1, 500):
            pw = generate_password(9)
            self.assertEqual(len(pw), 9)
            self.assertFalse(pw in pw_list)
            pw_list.append(pw)
            pw_hash = hash_password(pw)
            self.assertFalse(pw_hash in hash_list)
            hash_list.append(pw_hash)


class Test_010_PasswordGenerator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(Test_010_PasswordGenerator, self).__init__(*args, **kwargs)
        self.pws = []

    def test_0010_pw_length(self):
        for i in range(0, 100):
            length = random.randint(2, 12)
            pw = generate_password(length)
            self.assertEqual(len(pw), length)
            self.pws.append(pw)

    def test_0020_unique(self):
        for i in range(0, 100):
            self.pws.append(generate_password(8))

        self.assertEqual(len(self.pws), len(set(self.pws)))

    def test_0030_first_part_unique(self):
        pws = list(self.pws)
        pws = filter(lambda x: len(x) >= 6, pws)
        self.assertEqual(len(set(map(lambda x: x[:6], pws))), len(pws))
