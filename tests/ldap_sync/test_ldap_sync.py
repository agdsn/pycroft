# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
from unittest import TestCase

from pycroft.ldap_sync.exporter import LdapExporter, Record, RecordState, \
     config, _canonicalize_to_list
from pycroft.ldap_sync.action import Action, AddAction, DeleteAction, IdleAction, ModifyAction


class RecordTestCase(TestCase):
    def setUp(self):
        self.record = Record(dn='test', attrs={'bar': 'shizzle'})

    def test_record_equality(self):
        self.assertEqual(self.record, Record(dn='test', attrs={'bar': 'shizzle'}))

    def test_record_noncanonical_equality(self):
        self.assertEqual(self.record, Record(dn='test', attrs={'bar': ['shizzle']}))

    def test_record_subtraction_with_none_adds(self):
        difference = self.record - None
        self.assertIsInstance(difference, AddAction)
        self.assertEqual(difference.record, self.record)

    def test_none_subtracted_by_record_deletes(self):
        difference = None - self.record
        self.assertIsInstance(difference, DeleteAction)
        self.assertEqual(difference.record, self.record)

    def test_different_dn_raises_typeerror(self):
        with self.assertRaises(TypeError):
            # pylint: disable=expression-not-assigned
            self.record - Record(dn='notatest', attrs={})

    def test_same_record_subtraction_idles(self):
        difference = self.record - self.record
        self.assertIsInstance(difference, IdleAction)

    def test_correctly_different_record_modifies(self):
        difference = self.record - Record(dn='test', attrs={'bar': ''})
        self.assertIsInstance(difference, ModifyAction)

    def test_record_from_orm(self):
        # user = object()  #TODO: use actual ORM object
        # record = Record.from_db_user(user)
        # attrs = record.attrs
        # self.assertEqual(user.name, attrs['name'])
        # self.assertEqual(user.email, attrs['email'])
        # # … and so on.
        assert False

    def test_record_from_ldap_record(self):
        ldapsearch_record = {'dn': 'somedn',
                             'attributes': {'foo': u'bar', 'shizzle': u'baz'},
                             'raw_attributes': {'foo': b'bar'}}
        record = Record.from_ldap_record(ldapsearch_record)
        self.assertEqual(record.attrs, {'foo': [u'bar'], 'shizzle': [u'baz']})


class CanonicalizationTestCase(TestCase):
    def test_empty_string_gives_empty_list(self):
        self.assertEqual(_canonicalize_to_list(''), [])

    def test_none_gives_empty_list(self):
        self.assertEqual(_canonicalize_to_list(None), [])

    def test_zero_gets_kept(self):
        self.assertEqual(_canonicalize_to_list(0), [0])

    def test_string_gets_kept(self):
        self.assertEqual(_canonicalize_to_list('teststring'), ['teststring'])

    def test_false_gets_kept(self):
        self.assertEqual(_canonicalize_to_list(False), [False])

    def test_empty_list_gets_passed_identially(self):
        self.assertEqual(_canonicalize_to_list([]), [])

    def test_filled_list_gets_passed_identially(self):
        self.assertEqual(_canonicalize_to_list(['l', 'bar', 0, None]), ['l', 'bar', 0, None])


class RecordStateTestCase(TestCase):
    def setUp(self):
        self.record = Record(dn='test', attrs={})

    def test_equality_both_none(self):
        self.assertEqual(RecordState(), RecordState())

    def test_equality_only_current(self):
        self.assertEqual(RecordState(current=self.record), RecordState(current=self.record))

    def test_equality_only_desired(self):
        self.assertEqual(RecordState(desired=self.record), RecordState(desired=self.record))

    def test_equality_current_and_desired(self):
        self.assertEqual(RecordState(current=self.record, desired=self.record),
                         RecordState(current=self.record, desired=self.record))

    def test_not_equal_to_none(self):
        self.assertNotEqual(RecordState(), RecordState(current=self.record))


class ExporterInitializationTestCase(TestCase):
    def setUp(self):
        self.desired_user = Record(dn='user', attrs={})
        self.exporter = LdapExporter(desired=[self.desired_user], current=[])

    def test_one_record_state(self):
        self.assertEqual(len(self.exporter.states_dict), 1)
        state = self.exporter.states_dict[self.desired_user.dn]
        self.assertEqual(state, RecordState(current=None, desired=self.desired_user))


class EmptyLdapTestCase(TestCase):
    def setUp(self):
        self.desired_user = Record(dn='user', attrs={})
        self.exporter = LdapExporter(desired=[self.desired_user], current=[])
        self.exporter.compile_actions()

    def test_one_action_is_add(self):
        self.assertEqual(len(self.exporter.actions), 1)
        action = self.exporter.actions[0]
        self.assertIsInstance(action, AddAction)
        #TODO: test that the correct thing was added

# to test:
# - nonexistent record → add
# - obsolete record → del
# - nonexistent record → del


class BaseDNProxyTestCase(TestCase):
    def test_basedn_set_correctly(self):
        config.BASE_DN = 'shizzle'
        try:
            self.assertTrue(config.BASE_DN)
        except RuntimeError:
            self.fail("config.BASE_DN raised RuntimeError")

    def test_basedn_raises_when_not_set(self):
        with self.assertRaises(RuntimeError):
            config.BASE_DN  # pylint: disable=pointless-statement
