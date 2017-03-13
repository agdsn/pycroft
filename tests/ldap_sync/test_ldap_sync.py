# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
from unittest import TestCase

from pycroft.ldap_sync.exporter import LdapExporter
from pycroft.ldap_sync.record import Record, RecordState
from pycroft.ldap_sync.action import AddAction


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
