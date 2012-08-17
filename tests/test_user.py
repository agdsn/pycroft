# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import random
import unittest
from fixture import DataSet, SQLAlchemyFixture, DataTestCase
from crypt import crypt
from datetime import datetime
from passlib.hash import ldap_salted_sha1, ldap_md5_crypt, ldap_sha1_crypt

from pycroft.model import user, session
from pycroft.helpers.user_helper import generatePassword, hash_password, verify_password
from tests import FixtureDataTestBase


class DormitoryData(DataSet):
    class dummy_house:
        number = "01"
        short_name = "abc"
        street = "dummy"


class RoomData(DataSet):
    class dummy_room:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house


class UserData(DataSet):
    class dummy_user:
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room


class Test_010_PasswordGenerator(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(Test_010_PasswordGenerator, self).__init__(*args, **kwargs)
        self.pws = []

    def test_0010_pw_length(self):
        for i in range(0, 100):
            length = random.randint(2, 12)
            pw = generatePassword(length)
            self.assertEqual(len(pw), length)
            self.pws.append(pw)

    def test_0020_unique(self):
        for i in range(0, 100):
            self.pws.append(generatePassword(8))

        self.assertEqual(len(self.pws), len(set(self.pws)))

    def test_0030_first_part_unique(self):
        pws = list(self.pws)
        pws = filter(lambda x: len(x) >= 6, pws)
        self.assertEqual(len(set(map(lambda x: x[:6], pws))), len(pws))


class Test_020_PasswdHashes(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        self.hashes = []

        def crypt_pw(pw):
            return "{crypt}" + crypt(pw, generatePassword(2))

        self.methods = {"crypt": crypt_pw,
                        "CRYPT": ldap_sha1_crypt.encrypt,
                        "MD5": ldap_md5_crypt.encrypt,
                        "SSHA": ldap_salted_sha1.encrypt}

        for len in range(4,20):
            pw = generatePassword(len)
            hash_dict = {"plain": pw}
            for method in self.methods:
                hash_dict[method] = self.methods[method](pw)
            self.hashes.append(hash_dict)
        super(Test_020_PasswdHashes, self).__init__(*args, **kwargs)

    def test_0010_verify(self):
        for pw in self.hashes:
            for method in self.methods:
                self.assertTrue(verify_password(pw["plain"],  pw[method]), "%s: '%s' should verify with '%s'" % (method, pw[method], pw["plain"]))
                self.assertFalse(verify_password(pw["plain"], pw[method][len(method)+2:]))

    def test_0020_generate_hash(self):
        cur_type = "SSHA"
        for pw in self.hashes:
            self.assertNotEqual(hash_password(pw["plain"]), pw[cur_type], "Salt should be different!")
            self.assertTrue(hash_password(pw["plain"]).startswith("{%s}" % cur_type))

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

class Test_030_User_Passwords(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData]

    def test_0010_password_hash_validator(self):
        u = user.User.q.get(1)
        password = generatePassword(4)
        hash = hash_password(password)

        def set_hash(h):
            u.passwd_hash = h

        set_hash(hash)
        session.session.commit()

        self.assertRaisesRegexp(AssertionError, "A password-hash with les than 9 chars is not correct!", set_hash, password)
        session.session.commit()

        self.assertRaisesRegexp(AssertionError, "Cannot clear the password hash!", set_hash, None)
        session.session.commit()


    def test_0020_set_and_verify_password(self):
        u = user.User.q.get(1)
        password = generatePassword(4)
        hash = hash_password(password)

        u.set_password(password)
        session.session.commit()

        u = user.User.q.get(1)
        self.assertTrue(u.check_password(password))
        self.assertIsNotNone(user.User.verify_and_get(u.login, password))

        for length in range(0, 10):
            for cnt in range(1, 3):
                pw = generatePassword(length)
                if pw != password:
                    self.assertFalse(u.check_password(pw))
                    self.assertIsNone(user.User.verify_and_get(u.login, pw))
