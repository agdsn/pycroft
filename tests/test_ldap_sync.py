# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
from unittest import TestCase

from pycroft.ldap_sync.exporter import LdapExporter, Record, RecordState
from pycroft.ldap_sync.action import Action, AddAction, DeleteAction, IdleAction, ModifyAction


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


class RecordTestCase(TestCase):
    def setUp(self):
        self.record = Record(dn='test', attrs={'bar': 'shizzle'})

    def test_record_equality(self):
        self.assertEqual(self.record, Record(dn='test', attrs={'bar': 'shizzle'}))

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
        assert False

    def test_record_from_ldap_record(self):
        assert False

#TODO: check the ModifyAction constructor (correct attributes registered for
#update etc.)


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
