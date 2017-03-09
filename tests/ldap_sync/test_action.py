from unittest import TestCase

from pycroft.ldap_sync.exporter import Record
from pycroft.ldap_sync.action import Action, ModifyAction


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
        current_record = Record(dn=None, attrs=current)
        desired_record = Record(dn=None, attrs=desired)
        return ModifyAction.from_two_records(desired_record=desired_record,
                                             current_record=current_record)

    def test_desired_record_passed(self):
        desired = Record(dn=None, attrs={'foo': 'test'})
        current = Record(dn=None, attrs={})
        action = ModifyAction.from_two_records(desired_record=desired, current_record=current)
        self.assertEqual(action.record, desired)

    def test_one_attribute_changed(self):
        action = self.action_from_attrs(
            current={'foo': 'baz', 'email': 'admin@sci.hub'},
            desired={'foo': 'bar', 'email': 'admin@sci.hub'},
        )
        self.assertEqual(action.modifications, {'foo': 'bar'})

    def test_empty_attribute_emptied(self):
        action = self.action_from_attrs(
            current={'foo': 'bar', 'email': 'admin@sci.hub'},
            desired={'foo': 'bar', 'email': ''},
        )
        self.assertEqual(action.modifications, {'email': ''})

    def test_nongiven_attribute_doesnt_matter(self):
        action = self.action_from_attrs(
            current={'foo': 'bar', 'email': 'admin@sci.hub'},
            desired={'foo': 'bar'},
        )
        self.assertEqual(action.modifications, {})

    def test_new_attribute_will_be_set(self):
        action = self.action_from_attrs(
            current={'foo': 'bar'},
            desired={'foo': 'bar', 'email': 'admin@sci.hub'},
        )
        self.assertEqual(action.modifications, {'email': 'admin@sci.hub'})

    def test_attribute_none_will_be_set(self):
        action = self.action_from_attrs(
            current={'foo': 'bar'},
            desired={'foo': None},
        )
        self.assertEqual(action.modifications, {'foo': None})
