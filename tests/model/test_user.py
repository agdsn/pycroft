import random
import unittest
from crypt import crypt as python_crypt
from datetime import datetime
from passlib.hash import ldap_salted_sha1, ldap_md5_crypt, ldap_sha1_crypt

from pycroft.model import user, dormitory, session
from pycroft.helpers.user import generate_password, hash_password, verify_password, generate_crypt_salt
from tests import FixtureDataTestBase


from tests.model.fixtures.user_fixtures import DormitoryData, UserData, RoomData


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


class Test_020_PasswdHashes(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        self.hashes = []

        def crypt_pw(pw):
            return "{crypt}" + python_crypt(pw, generate_crypt_salt(2))

        self.methods = {"crypt": crypt_pw,
                        "CRYPT": ldap_sha1_crypt.encrypt,
                        "MD5": ldap_md5_crypt.encrypt,
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
            pw = generate_password(9)
            self.assertEqual(len(pw), 9)
            self.assertFalse(pw in pw_list)
            pw_list.append(pw)
            pw_hash = hash_password(pw)
            self.assertFalse(pw_hash in hash_list)
            hash_list.append(pw_hash)

class Test_030_User_Passwords(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData]

    def test_0010_password_hash_validator(self):
        u = user.User.q.get(1)
        password = generate_password(4)
        pw_hash = hash_password(password)

        def set_hash(h):
            u.passwd_hash = h

        set_hash(pw_hash)
        session.session.commit()

        self.assertRaisesRegexp(AssertionError, "A password-hash with les than 9 chars is not correct!", set_hash, password)
        session.session.commit()

        self.assertRaisesRegexp(AssertionError, "Cannot clear the password hash!", set_hash, None)
        session.session.commit()


    def test_0020_set_and_verify_password(self):
        u = user.User.q.get(1)
        password = generate_password(4)
        pw_hash = hash_password(password)

        u.set_password(password)
        session.session.commit()

        u = user.User.q.get(1)
        self.assertTrue(u.check_password(password))
        self.assertIsNotNone(user.User.verify_and_get(u.login, password))
        self.assertEqual(user.User.verify_and_get(u.login, password), u)

        self.assertIsNone(user.User.verify_and_get(password, u.login))

        for length in range(0, 10):
            for cnt in range(1, 3):
                pw = generate_password(length)
                if pw != password:
                    self.assertFalse(u.check_password(pw))
                    self.assertIsNone(user.User.verify_and_get(u.login, pw))


class Test_040_User_Login(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData]

    def test_0010_user_login_validator(self):
        u = user.User(name="John Doe", registration_date=datetime.now(), room=dormitory.Room.q.get(1))

        def set_login(login):
            u.login = login

        for length in range(1, 30):
            if 2 < length < 23:
                set_login("a" * length)
            else:
                self.assertRaisesRegexp(Exception, "invalid unix-login!", set_login, "a" * length)

        valid = ["abcdefg", "a_b", "a3b", "a_2b", "a33", "a__4"]
        invalid = ["123", "ABC", "3bc", "_ab", "ab_", "3b_", "_b3", "&&"]
        blocked = ["root", "daemon", "bin", "sys", "sync", "games", "man", "lp", "mail",
                   "news", "uucp", "proxy", "majordom", "postgres", "wwwadmin", "backup",
                   "msql", "operator", "ftp", "ftpadmin", "guest", "bb", "nobody"]

        for login in valid:
            set_login(login)
        for login in invalid:
            self.assertRaisesRegexp(Exception, "invalid unix-login!", set_login, login)
        for login in blocked:
            self.assertRaisesRegexp(Exception, "invalid unix-login!", set_login, login)

        u = user.User.q.get(1)
        self.assertRaisesRegexp(AssertionError, "user already in the database - cannot change login anymore!", set_login, "abc")

