from unittest import TestCase

import ldap3

from ldap_sync.record import UserRecord, dn_from_username
from ldap_sync.action import Action, IdleAction, AddAction, ModifyAction, \
     DeleteAction


class ActionSubclassTestCase(TestCase):
    def test_instantiation_fails(self):
        with self.assertRaises(TypeError):
            Action(record=None)

    def test_subclassing_with_execute_works(self):
        class A(Action):
            def execute(self):
                pass
        try:
            A(record=None)
        except TypeError as e:
            self.fail("Subclassing raised Exception {}".format(e))


class ModifyActionConstructorTestCase(TestCase):
    def action_from_attrs(self, current, desired):
        current_record = UserRecord(dn=None, attrs=current)
        desired_record = UserRecord(dn=None, attrs=desired)
        return ModifyAction.from_two_records(desired_record=desired_record,
                                             current_record=current_record)

    def test_desired_record_passed(self):
        desired = UserRecord(dn=None, attrs={'gecos': 'test'})
        current = UserRecord(dn=None, attrs={})
        action = ModifyAction.from_two_records(desired_record=desired, current_record=current)
        self.assertEqual(action.record, desired)

    def test_one_attribute_changed(self):
        action = self.action_from_attrs(
            current={'gecos': 'baz', 'mail': 'admin@sci.hub'},
            desired={'gecos': 'bar', 'mail': 'admin@sci.hub'},
        )
        self.assertEqual(action.modifications, {'gecos': ['bar']})

    def test_empty_attribute_emptied(self):
        action = self.action_from_attrs(
            current={'gecos': 'bar', 'mail': 'admin@sci.hub'},
            desired={'gecos': 'bar', 'mail': ''},
        )
        self.assertEqual(action.modifications, {'mail': []})

    def test_new_attribute_will_be_set(self):
        action = self.action_from_attrs(
            current={'foo': 'bar'},
            desired={'foo': 'bar', 'mail': 'admin@sci.hub'},
        )
        self.assertEqual(action.modifications, {'mail': ['admin@sci.hub']})

    def test_attribute_none_will_be_set(self):
        action = self.action_from_attrs(
            current={'gecos': 'bar'},
            desired={'gecos': None},
        )
        self.assertEqual(action.modifications, {'gecos': []})


class MockedLdapTestBase(TestCase):
    base = 'ou=Nutzer,ou=Pycroft,dc=AG DSN,dc=de'

    def setUp(self):
        self.server = ldap3.Server('fake_server', get_info=ldap3.ALL)
        self.connection = ldap3.Connection(self.server, user='cn=test', password='pw',
                                           client_strategy=ldap3.MOCK_SYNC)
        self.connection.open()
        self.single_valued_attributes = ()

    def get_all_objects(self):
        self.connection.search(search_base=self.base, search_filter='(objectclass=*)',
                               attributes='*')
        return self.connection.response

    def validate_attribute_type(self, key, value):
        """Validate if some attribute value has the correct type.

        This concerns the single-valuedness, which is estimated using
        a hard-coded, global list :py:obj:`SINGLE_VALUED_ATTRIBUTES`
        capturing teh most relevant attributes restricted to a single
        value.
        """
        if key in SINGLE_VALUED_ATTRIBUTES and isinstance(value, list):
            raise ValueError("Value '{}' for key '{}' should be a single value"
                             .format(value, key))
        if key not in SINGLE_VALUED_ATTRIBUTES and not isinstance(value, list):
            raise ValueError("Value '{}' for key '{}' should be a list"
                             .format(value, key))

    def tearDown(self):
        self.connection.strategy.close()  # unbinds connection


SINGLE_VALUED_ATTRIBUTES = ['uidNumber', 'gidNumber', 'homeDirectory',
                            'gecos', 'shadowMin', 'shadowMax',
                            'shadowFlag', 'shadowExpire', 'loginShell']


class AddActionTestCase(MockedLdapTestBase):
    def setUp(self):
        super(AddActionTestCase, self).setUp()
        self.attributes = {'objectClass': UserRecord.LDAP_OBJECTCLASSES,
                           'mail': ['bas'],
                           'userPassword': ['$1$dtruiandetnuhgaldrensutrhawtruhs']}
        self.uid = 'shizzle'
        self.dn = dn_from_username(self.uid, base=self.base)
        record = UserRecord(dn=self.dn, attrs=self.attributes)
        action = AddAction(record=record)

        action.execute(self.connection)

        self.objects = self.get_all_objects()

    def test_dn_correct(self):
        self.assertEqual(self.objects[0]['dn'], self.dn)

    def test_correct_uid_in_attributes(self):
        attrs = self.objects[0]['attributes']
        # uid is not SINGLE VALUE according to schema
        self.assertEqual(attrs['uid'][0], self.uid)

    def test_correct_objectclasses(self):
        classes = self.objects[0]['attributes']['objectClass']
        self.assertEqual(classes, UserRecord.LDAP_OBJECTCLASSES)

    def test_other_attributes_passed(self):
        received_attributes = self.objects[0]['attributes']
        for key, value in self.attributes.items():
            self.validate_attribute_type(key=key, value=value)
            self.assertIn(key, received_attributes)
            self.assertEqual(received_attributes[key], value)


class DeleteActionTestCase(MockedLdapTestBase):
    def setUp(self):
        super(DeleteActionTestCase, self).setUp()
        self.uid = 'shizzle'
        self.dn = dn_from_username(self.uid, base=self.base)
        self.connection.add(self.dn, UserRecord.LDAP_OBJECTCLASSES)
        record = UserRecord(dn=self.dn, attrs={})
        DeleteAction(record=record).execute(self.connection)

    def test_no_objects(self):
        self.assertEqual(len(self.get_all_objects()), 0)


class ModifyActionTestCase(MockedLdapTestBase):
    def setUp(self):
        super(ModifyActionTestCase, self).setUp()
        self.uid = 'shizzle'
        self.dn = dn_from_username(self.uid, base=self.base)
        self.connection.add(self.dn, UserRecord.LDAP_OBJECTCLASSES)
        record = UserRecord(dn=self.dn, attrs={})
        action = ModifyAction(record=record, modifications={'mail': 'new@shizzle.de'})
        action.execute(self.connection)

    def test_one_object_changed(self):
        objs = self.get_all_objects()
        self.assertEqual(len(objs), 1)

    def test_mail_changed(self):
        self.assertEqual(self.get_all_objects()[0]['attributes']['mail'],
                         ['new@shizzle.de'])


class IdleActionTestCase(TestCase):
    def test_execute_does_nothing(self):
        record = UserRecord(dn='test', attrs={})
        IdleAction(record=record).execute()
