# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
import logging
from unittest import TestCase

from pycroft.model.session import session
from pycroft.ldap_sync.exporter import LdapExporter, fetch_users_to_sync, get_config
from pycroft.ldap_sync.record import Record, RecordState
from pycroft.ldap_sync.action import AddAction
from tests import FixtureDataTestBase
from tests.fixtures.dummy.user import UserData
import tests.fixtures.ldap_sync.simple as simple_fixtures
import tests.fixtures.ldap_sync.complex as complex_fixtures


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

class LdapSyncLoggerMutedMixin(object):
    def setUp(self):
        super(LdapSyncLoggerMutedMixin, self).setUp()
        logging.getLogger('ldap_sync').addHandler(logging.NullHandler())


class EmptyDatabaseTestCase(LdapSyncLoggerMutedMixin, FixtureDataTestBase):
    # These datasets provide two users without the `mail` attribute.  One of
    # them has a unix account.
    datasets = [UserData]

    def setUp(self):
        super(EmptyDatabaseTestCase, self).setUp()
        self.users = fetch_users_to_sync(session)

    def test_no_users_fetched(self):
        self.assertEqual(self.users, [])


class OneUserFetchTestCase(LdapSyncLoggerMutedMixin, FixtureDataTestBase):
    # These datasets provide two users with `mail` attributes, while only one
    # of them has a unix account.
    datasets = simple_fixtures.datasets

    def test_one_user_fetched(self):
        users = fetch_users_to_sync(session)
        self.assertEqual(len(users), 1)


class MultipleUsersFilterTestCase(FixtureDataTestBase):
    datasets = complex_fixtures.datasets

    def test_correct_users_fetched(self):
        users = fetch_users_to_sync(session)
        expected_logins = [
            complex_fixtures.UserData.active_user1.login,
            complex_fixtures.UserData.active_user2.login,
        ]
        self.assertEqual([u.login for u in users], expected_logins)
