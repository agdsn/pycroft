# -*- coding: utf-8 -*-
from unittest import TestCase

from legacy.ldap_model import Nutzer


class LdapNutzerFromRecordTestCase(TestCase):
    def setUp(self):
        super(LdapNutzerFromRecordTestCase, self).setUp()
        self.given_attrs = {
            'uid': ['user'],
            'mail': ['foo@bar.baz'],
            'userPassword': ['{CRYPT}'],
            'homeDirectory': '/home/user',
            'uidNumber': 10010,
            'gidNumber': 100,
            'loginShell': '/bin/zsh',
        }
        self.expected_attrs = {
            'uid': 'user',
            'mail': 'foo@bar.baz',
            'userPassword': '{CRYPT}',
            'homeDirectory': '/home/user',
            'uidNumber': 10010,
            'gidNumber': 100,
            'loginShell': '/bin/zsh',
        }

    def assert_attributes_passed(self, nutzer, expected_attributes):
        for attr, value in list(expected_attributes.items()):
            self.assertEqual(getattr(nutzer, attr), value)


    def test_complete_attributes_work(self):
        nutzer = Nutzer.from_ldap_attributes(self.given_attrs)
        self.assert_attributes_passed(nutzer, self.expected_attrs)

    def test_mail_optional(self):
        nutzer = Nutzer.from_ldap_attributes({
            key: val for key, val in list(self.given_attrs.items())
            if key != 'mail'
        })
        expected = {key: val for key, val in list(self.expected_attrs.items())
                    if key != 'mail'}
        expected.update(mail=None)
        self.assert_attributes_passed(nutzer, expected)

    def test_password_obligatory(self):
        attrs = {key: value for key, value in list(self.given_attrs.items())
                 if key != 'userPassword'}
        with self.assertRaises(KeyError):
            Nutzer.from_ldap_attributes(attrs)
