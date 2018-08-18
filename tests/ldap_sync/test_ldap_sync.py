# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
import logging
import sys
from unittest import TestCase

import ldap3

from pycroft.model.session import session
from ldap_sync.exporter import LdapExporter, fetch_users_to_sync, get_config, \
     establish_and_return_ldap_connection, fetch_current_ldap_users, sync_all
if sys.version_info >= (3,5):
    from ldap_sync.exporter import _ResultProxyType
from ldap_sync.record import Record, RecordState
from ldap_sync.action import AddAction, IdleAction, DeleteAction, ModifyAction
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
        users = fetch_users_to_sync(session, required_property='mail')
        self.assertEqual(len(users), 1)


class MultipleUsersFilterTestCase(FixtureDataTestBase):
    datasets = complex_fixtures.datasets

    def test_correct_users_fetched(self):
        users = fetch_users_to_sync(session, required_property='mail')
        expected_logins = {
            complex_fixtures.UserData.active_user1.login,
            complex_fixtures.UserData.active_user2.login,
        }
        self.assertEqual({u.User.login for u in users}, expected_logins)


class LdapTestBase(LdapSyncLoggerMutedMixin, TestCase):
    @classmethod
    def setUpClass(cls):
        super(LdapTestBase, cls).setUpClass()
        try:
            cls.config = get_config(required_property='mail')
        except KeyError as e:
            raise RuntimeError("Environment variable {} must be set".format(e.args[0]))
        cls.base_dn = cls.config.base_dn

    def setUp(self):
        super(LdapTestBase, self).setUp()
        self.conn = self._establish_connection_and_return()
        self._clean_ldap_base()

    def _establish_connection_and_return(self):
        self.server = ldap3.Server(host=self.config.host, port=self.config.port)
        return ldap3.Connection(self.server, user=self.config.bind_dn,
                                password=self.config.bind_pw, auto_bind=True)

    def _clean_ldap_base(self):
        """Delete and recreate the base and set up a default ppolicy."""
        self.conn.search(self.base_dn, '(objectclass=*)')
        if self.conn.entries:
            for response_item in self.conn.response:
                self.conn.delete(response_item['dn'])

        self.conn.delete(self.base_dn)

        result = self.conn.add(self.base_dn, 'organizationalUnit')
        if not result:
            raise RuntimeError("Couldn't create base_dn {} as organizationalUnit"
                               .format(self.base_dn), self.conn.result)

        # PASSWORD POLICIES
        # mimicking the LDIF given in https://hub.docker.com/r/dinkel/openldap/

        policies_dn = "ou=policies,{base}".format(base=self.base_dn)
        result = self.conn.add(policies_dn, 'organizationalUnit')

        if not result:
            raise RuntimeError("Couldn't create policies_dn {} as organizationalUnit"
                               .format(policies_dn), self.conn.result)

        default_ppolicy_dn = "cn=default,{}".format(policies_dn)
        policy_attrs = {
            'pwdAllowUserChange': True,
            'pwdAttribute': "userPassword",
            'pwdCheckQuality': 1,
            'pwdExpireWarning': 604800,  # 7 days
            'pwdFailureCountInterval': 0,
            'pwdGraceAuthNLimit': 0,
            'pwdInHistory': 5,
            'pwdLockout': True,
            'pwdLockoutDuration': 1800,  # 30 minutes
            'pwdMaxAge': 15552000,  # 180 days
            'pwdMaxFailure': 5,
            'pwdMinAge': 0,
            'pwdMinLength': 6,
            'pwdMustChange': True,
        }

        result = self.conn.add(default_ppolicy_dn,
                               ['applicationProcess', 'pwdPolicy'],
                               policy_attrs)

    def tearDown(self):
        self.conn.unbind()


class LdapFunctionalityTestCase(LdapTestBase):
    def test_ldap_base_exists(self):
        success = self.conn.search(self.base_dn, '(objectclass=*)', ldap3.BASE)
        if not success:
            self.fail("Base DN search failed: {}".format(self.conn.result))

    def test_adding_an_entry_works(self):
        self.conn.add('uid=bar,{}'.format(self.base_dn), ['inetOrgPerson'],
                      {'sn': 'test', 'cn': 'test'})
        success = self.conn.search(self.base_dn, '(objectclass=inetOrgPerson)')
        if not success:
            self.fail("Base DN subtree search failed: {}".format(self.conn.result))
        relevant_entries = [r for r in self.conn.response if r['dn'] != self.base_dn]
        self.assertEqual(len(relevant_entries), 1)


class LdapSyncerTestBase(LdapTestBase, FixtureDataTestBase):
    datasets = complex_fixtures.datasets

    def setUp(self):
        super(LdapSyncerTestBase, self).setUp()
        self.users_to_sync = fetch_users_to_sync(session, self.config.required_property)
        self.initial_ldap_users = fetch_current_ldap_users(self.conn, base_dn=self.base_dn)

    def build_exporter(self, current=None, desired=None):
        """Return an LdapExporter from ldap and orm users

        It does not compile actions.
        """
        if current is None:
            current = self.initial_ldap_users
        if desired is None:
            desired = self.users_to_sync
        return LdapExporter.from_orm_objects_and_ldap_result(
            current=current,
            desired=desired,
            base_dn=self.base_dn,
        )

    def sync_all(self):
        sync_all(db_users=self.users_to_sync, ldap_users=self.initial_ldap_users,
                 connection=self.conn, base_dn=self.base_dn)


class LdapTestCase(LdapSyncerTestBase):
    def test_connection_works(self):
        conn = establish_and_return_ldap_connection(
            host=self.config.host, port=self.config.port,
            bind_dn=self.config.bind_dn, bind_pw=self.config.bind_pw
        )
        self.assertTrue(conn.bound)
        result = conn.search(self.base_dn, '(objectclass=*)', ldap3.BASE)
        self.assertTrue(result)

    def test_no_current_ldap_users(self):
        self.assertEqual(self.initial_ldap_users, [])

    def test_syncall_adds_users(self):
        self.sync_all()
        new_users = fetch_current_ldap_users(self.conn, base_dn=self.base_dn)
        self.assertEqual(len(new_users), len(self.users_to_sync))

    def test_exporter_compiles_all_addactions(self):
        exporter = self.build_exporter()
        exporter.compile_actions()
        self.assertEqual(len(exporter.actions), len(self.users_to_sync))
        self.assertTrue(isinstance(a, AddAction) for a in exporter.actions)

        exporter.execute_all(self.conn)
        new_users = fetch_current_ldap_users(self.conn, base_dn=self.base_dn)
        self.assertEqual(len(new_users), len(self.users_to_sync))


class LdapOnceSyncedTestCase(LdapSyncerTestBase):
    def setUp(self):
        super(LdapOnceSyncedTestCase, self).setUp()
        self.sync_all()
        # In comparison to `initial_ldap_users`:
        self.new_ldap_users = fetch_current_ldap_users(self.conn, base_dn=self.base_dn)

    def test_idempotency_of_two_syncs(self):
        self.sync_all()
        exporter = self.build_exporter()
        exporter.compile_actions()
        self.assertEqual(len(exporter.actions), len(self.users_to_sync))
        self.assertTrue(isinstance(a, IdleAction) for a in exporter.actions)

    def test_attributes_synced_correctly(self):
        records = {}
        for result in self.users_to_sync:
            record = Record.from_db_user(result.User, self.base_dn,
                                         should_be_blocked=result.should_be_blocked)
            records[record.dn] = record

        for ldap_user in self.new_ldap_users:
            ldap_record = Record.from_ldap_record(ldap_user)
            # Due to the canonicalization, empty attributes will appear in
            # `records`.  We want to ignore those for the comparison.
            effective_attributes_in_db = {
                key: val
                for key, val in records[ldap_record.dn].attrs.items()
                if val != []
            }
            self.assertEqual(effective_attributes_in_db,
                             {k: v for k,v in ldap_record.attrs.items()
                              if k in effective_attributes_in_db})

    def test_mail_deletion(self):
        users_with_mail = [u for u in self.users_to_sync if u.User.email is not None]
        if not users_with_mail:
            raise RuntimeError("Fixtures do not provide a syncable user with a mail address")

        modified_user = users_with_mail[0].User
        mod_dn = Record.from_db_user(modified_user, self.base_dn).dn
        modified_user.email = 'bar@agdsn.de'
        session.add(modified_user)
        session.commit()

        self.users_to_sync = fetch_users_to_sync(session, self.config.required_property)
        self.sync_all()

        newest_users = fetch_current_ldap_users(self.conn, base_dn=self.base_dn)
        newest_users_correct_dn = [u for u in newest_users if u['dn'] == mod_dn]
        self.assertEqual(len(newest_users_correct_dn), 1)
        modified_record = newest_users_correct_dn[0]
        self.assertNotIn('mail', modified_record)

    def test_mail_creation(self):
        users_without_mail = [u for u in self.users_to_sync if u.User.email is None]
        if not users_without_mail:
            raise RuntimeError("Fixtures do not provide a syncable user without a mail address")
        mod_user = users_without_mail[0].User
        mod_dn = Record.from_db_user(mod_user, self.base_dn).dn
        mod_user.email = 'bar@agdsn.de'
        session.add(mod_user)
        session.commit()

        users_to_sync = fetch_users_to_sync(session, self.config.required_property)
        exporter = self.build_exporter(current=self.new_ldap_users,
                                       desired=users_to_sync)
        exporter.compile_actions()
        relevant_actions = [a for a in exporter.actions if not isinstance(a, IdleAction)]
        print(relevant_actions)
        self.assertEqual(len(relevant_actions), 1)
        self.assertEqual(type(relevant_actions[0]), ModifyAction)
        exporter.execute_all(self.conn)

        newest_users = fetch_current_ldap_users(self.conn, base_dn=self.base_dn)
        modified_ldap_record = [u for u in newest_users if u['dn'] == mod_dn][0]
        self.assertIn('mail', modified_ldap_record['attributes'])
        self.assertEqual(modified_ldap_record['attributes']['mail'], [mod_user.email])

    def test_no_desired_records_removes_everything(self):
        exporter = self.build_exporter(current=self.new_ldap_users, desired=[])
        exporter.compile_actions()

        # Test the actions are correct
        self.assertEqual(len(exporter.actions), len(self.new_ldap_users))
        for action in exporter.actions:
            self.assertEqual(type(action), DeleteAction)

        # Actually execute these and check they delete everything
        exporter.execute_all(self.conn)

        newest_users = fetch_current_ldap_users(self.conn, base_dn=self.base_dn)
        self.assertEqual(newest_users, [])
