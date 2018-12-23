# -*- coding: utf-8 -*-
# pylint: disable=missing-docstring
import logging
import sys
from unittest import TestCase

import ldap3

from pycroft.model.session import session
from ldap_sync.exporter import LdapExporter, fetch_users_to_sync, fetch_groups_to_sync, \
    fetch_properties_to_sync, get_config, establish_and_return_ldap_connection, \
    fetch_current_ldap_users, fetch_current_ldap_groups, fetch_current_ldap_properties, sync_all
from ldap_sync.record import UserRecord, GroupRecord, RecordState
from ldap_sync.action import AddAction, IdleAction, DeleteAction, ModifyAction
from tests import FixtureDataTestBase
from tests.fixtures.dummy.user import UserData
import tests.fixtures.ldap_sync.simple as simple_fixtures
import tests.fixtures.ldap_sync.complex as complex_fixtures


class ExporterInitializationTestCase(TestCase):
    def setUp(self):
        self.desired_user = UserRecord(dn='user', attrs={})
        self.exporter = LdapExporter(desired=[self.desired_user], current=[])

    def test_one_record_state(self):
        self.assertEqual(len(self.exporter.states_dict), 1)
        state = self.exporter.states_dict[self.desired_user.dn]
        self.assertEqual(state, RecordState(current=None, desired=self.desired_user))


class EmptyLdapTestCase(TestCase):
    def setUp(self):
        self.desired_user = UserRecord(dn='user', attrs={})
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

    def test_one_group_fetched(self):
        groups = [group for group in fetch_groups_to_sync(session) if
                  group.Group.name == simple_fixtures.MembershipData.dummy_membership.group.name]
        self.assertEqual(len(groups), 1)
        expected_members = {
            simple_fixtures.UserData.withldap.login
        }
        self.assertEqual(set(groups[0].members), expected_members)

    def test_one_property_fetched(self):
        properties = [prop for prop in fetch_properties_to_sync(session) if
                      prop.name == simple_fixtures.PropertyData.mail.name]
        self.assertEqual(len(properties), 1)
        expected_members = {
            simple_fixtures.UserData.withldap.login
        }
        self.assertEqual(set(properties[0].members), expected_members)


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
            cls.config = get_config(required_property='mail', use_ssl='False',
                                    ca_certs_file=None, ca_certs_data=None)
        except KeyError as e:
            raise RuntimeError("Environment variable {} must be set".format(e.args[0]))
        cls.base_dn = cls.config.base_dn
        cls.user_base_dn = 'ou=users,{}'.format(cls.config.base_dn)
        cls.group_base_dn = 'ou=groups,{}'.format(cls.config.base_dn)
        cls.property_base_dn = 'ou=properties,{}'.format(cls.config.base_dn)

    def setUp(self):
        super(LdapTestBase, self).setUp()
        self.conn = self._establish_connection_and_return()
        self._clean_ldap_base()

    def _establish_connection_and_return(self):
        self.server = ldap3.Server(host=self.config.host, port=self.config.port)
        return ldap3.Connection(self.server, user=self.config.bind_dn,
                                password=self.config.bind_pw, auto_bind=True)

    def _recursive_delete(self, base_dn):
        self.conn.search(base_dn, '(objectclass=*)', ldap3.LEVEL)
        for response_item in self.conn.response:
            self._recursive_delete(response_item['dn'])
        self.conn.delete(base_dn)

    def _clean_ldap_base(self):
        """Delete and recreate the base and set up a default ppolicy."""
        self._recursive_delete(self.base_dn)

        for base_dn in (self.base_dn, self.user_base_dn, self.group_base_dn, self.property_base_dn):
            result = self.conn.add(base_dn, 'organizationalUnit')
            if not result:
                raise RuntimeError("Couldn't create base_dn {} as organizationalUnit"
                                   .format(base_dn), self.conn.result)

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
        self.initial_ldap_users = fetch_current_ldap_users(self.conn, base_dn=self.user_base_dn)
        self.groups_to_sync = fetch_groups_to_sync(session)
        self.initial_ldap_groups = fetch_current_ldap_groups(self.conn, base_dn=self.group_base_dn)
        self.properties_to_sync = fetch_properties_to_sync(session)
        self.initial_ldap_properties = fetch_current_ldap_properties(self.conn, base_dn=self.property_base_dn)

    def build_exporter(self):
        """Return an LdapExporter.

        It does not compile actions.
        """
        return LdapExporter.from_orm_objects_and_ldap_result(
            db_users=self.users_to_sync,
            ldap_users=self.initial_ldap_users,
            user_base_dn=self.user_base_dn,
            db_groups=self.groups_to_sync,
            ldap_groups=self.initial_ldap_groups,
            group_base_dn=self.group_base_dn,
            db_properties=self.properties_to_sync,
            ldap_properties=self.initial_ldap_properties,
            property_base_dn=self.property_base_dn,
        )

    def build_user_exporter(self, current_users=None, desired_users=None):
        """Return an LdapExporter from ldap and orm users.

        It does not compile actions.
        """
        if current_users is None:
            current_users = self.initial_ldap_users

        if desired_users is None:
            desired_users = self.users_to_sync

        return LdapExporter.from_orm_objects_and_ldap_result(
            db_users=desired_users,
            ldap_users=current_users,
            user_base_dn=self.user_base_dn,
        )

    def sync_all(self):
        sync_all(connection=self.conn, ldap_users=self.initial_ldap_users,
                 db_users=self.users_to_sync, user_base_dn=self.user_base_dn,
                 ldap_groups=self.initial_ldap_groups,
                 db_groups=self.groups_to_sync,
                 group_base_dn=self.group_base_dn,
                 ldap_properties=self.initial_ldap_properties,
                 db_properties=self.properties_to_sync,
                 property_base_dn=self.property_base_dn)


class LdapTestCase(LdapSyncerTestBase):
    def test_connection_works(self):
        conn = establish_and_return_ldap_connection(
            host=self.config.host, port=self.config.port,
            use_ssl=self.config.use_ssl, ca_certs_file=None, ca_certs_data=None,
            bind_dn=self.config.bind_dn, bind_pw=self.config.bind_pw
        )
        self.assertTrue(conn.bound)
        result = conn.search(self.base_dn, '(objectclass=*)', ldap3.BASE)
        self.assertTrue(result)

    def test_no_current_ldap_entries(self):
        self.assertEqual(self.initial_ldap_users, [])
        self.assertEqual(self.initial_ldap_groups, [])
        self.assertEqual(self.initial_ldap_properties, [])

    def assert_entries_synced(self):
        new_users = fetch_current_ldap_users(self.conn, base_dn=self.user_base_dn)
        self.assertEqual(len(new_users), len(self.users_to_sync))
        new_groups = fetch_current_ldap_groups(self.conn, base_dn=self.group_base_dn)
        self.assertEqual(len(new_groups), len(self.groups_to_sync))
        new_properties = fetch_current_ldap_properties(self.conn, base_dn=self.property_base_dn)
        self.assertEqual(len(new_properties), len(self.properties_to_sync))

    def test_syncall_adds_entries(self):
        self.sync_all()
        self.assert_entries_synced()

    def test_exporter_compiles_all_addactions(self):
        exporter = self.build_exporter()
        exporter.compile_actions()
        self.assertEqual(
            len(exporter.actions),
            len(self.users_to_sync) + len(self.groups_to_sync) + len(self.properties_to_sync))
        self.assertTrue(isinstance(a, AddAction) for a in exporter.actions)

        exporter.execute_all(self.conn)
        self.assert_entries_synced()


class LdapOnceSyncedTestCase(LdapSyncerTestBase):
    def setUp(self):
        super(LdapOnceSyncedTestCase, self).setUp()
        self.sync_all()
        # In comparison to `initial_ldap_users`:
        self.new_ldap_users = fetch_current_ldap_users(self.conn, base_dn=self.user_base_dn)
        self.new_ldap_groups = fetch_current_ldap_groups(self.conn, base_dn=self.group_base_dn)
        self.new_ldap_properties = fetch_current_ldap_properties(self.conn, base_dn=self.property_base_dn)

    def test_idempotency_of_two_syncs(self):
        self.sync_all()
        exporter = self.build_exporter()
        exporter.compile_actions()
        self.assertEqual(
            len(exporter.actions),
            len(self.users_to_sync) + len(self.groups_to_sync) + len(self.properties_to_sync))
        self.assertTrue(isinstance(a, IdleAction) for a in exporter.actions)

    def assert_attributes_equal(self, expected, actual):
        # Due to the canonicalization, empty attributes will appear in
        # `expected`.  We want to ignore those for the comparison.
        effective_attributes_in_db = {
            key: val
            for key, val in expected.attrs.items()
            if val != []
        }
        self.assertEqual(effective_attributes_in_db,
                         {k: v for k, v in actual.attrs.items()
                          if k in effective_attributes_in_db})

    def test_user_attributes_synced_correctly(self):
        records = {}
        for result in self.users_to_sync:
            record = UserRecord.from_db_user(result.User, self.user_base_dn,
                                         should_be_blocked=result.should_be_blocked)
            records[record.dn] = record

        for ldap_user in self.new_ldap_users:
            ldap_record = UserRecord.from_ldap_record(ldap_user)
            self.assert_attributes_equal(records[ldap_record.dn], ldap_record)

    def filter_members(self, members):
        """Remove users that are not exported."""
        return [m for m in members if any(u.User.login == m for u in self.users_to_sync)]

    def test_group_attributes_synced_correctly(self):
        records = {}
        for group in self.groups_to_sync:
            record = GroupRecord.from_db_group(group.Group.name, self.filter_members(group.members),
                                               self.group_base_dn, self.user_base_dn)
            records[record.dn] = record

        for ldap_group in self.new_ldap_groups:
            ldap_record = GroupRecord.from_ldap_record(ldap_group)
            self.assert_attributes_equal(records[ldap_record.dn], ldap_record)

    def test_property_attributes_synced_correctly(self):
        records = {}
        for property in self.properties_to_sync:
            record = GroupRecord.from_db_group(property.name, self.filter_members(property.members),
                                               self.property_base_dn, self.user_base_dn)
            records[record.dn] = record

        for ldap_property in self.new_ldap_properties:
            ldap_record = GroupRecord.from_ldap_record(ldap_property)
            self.assert_attributes_equal(records[ldap_record.dn], ldap_record)


    def test_mail_deletion(self):
        users_with_mail = [u for u in self.users_to_sync if u.User.email is not None]
        if not users_with_mail:
            raise RuntimeError("Fixtures do not provide a syncable user with a mail address")

        modified_user = users_with_mail[0].User
        mod_dn = UserRecord.from_db_user(modified_user, self.user_base_dn).dn
        modified_user.email = 'bar@agdsn.de'
        session.add(modified_user)
        session.commit()

        self.users_to_sync = fetch_users_to_sync(session, self.config.required_property)
        self.sync_all()

        newest_users = fetch_current_ldap_users(self.conn, base_dn=self.user_base_dn)
        newest_users_correct_dn = [u for u in newest_users if u['dn'] == mod_dn]
        self.assertEqual(len(newest_users_correct_dn), 1)
        modified_record = newest_users_correct_dn[0]
        self.assertNotIn('mail', modified_record)

    def test_mail_creation(self):
        users_without_mail = [u for u in self.users_to_sync if u.User.email is None]
        if not users_without_mail:
            raise RuntimeError("Fixtures do not provide a syncable user without a mail address")
        mod_user = users_without_mail[0].User
        mod_dn = UserRecord.from_db_user(mod_user, self.user_base_dn).dn
        mod_user.email = 'bar@agdsn.de'
        session.add(mod_user)
        session.commit()

        users_to_sync = fetch_users_to_sync(session, self.config.required_property)
        exporter = self.build_user_exporter(current_users=self.new_ldap_users,
                                       desired_users=users_to_sync)
        exporter.compile_actions()
        relevant_actions = [a for a in exporter.actions if not isinstance(a, IdleAction)]
        print(relevant_actions)
        self.assertEqual(len(relevant_actions), 1)
        self.assertEqual(type(relevant_actions[0]), ModifyAction)
        exporter.execute_all(self.conn)

        newest_users = fetch_current_ldap_users(self.conn, base_dn=self.user_base_dn)
        modified_ldap_record = [u for u in newest_users if u['dn'] == mod_dn][0]
        self.assertIn('mail', modified_ldap_record['attributes'])
        self.assertEqual(modified_ldap_record['attributes']['mail'], [mod_user.email])

    def test_no_desired_records_removes_everything(self):
        exporter = self.build_user_exporter(current_users=self.new_ldap_users, desired_users=[])
        exporter.compile_actions()

        # Test the actions are correct
        self.assertEqual(len(exporter.actions), len(self.new_ldap_users))
        for action in exporter.actions:
            self.assertEqual(type(action), DeleteAction)

        # Actually execute these and check they delete everything
        exporter.execute_all(self.conn)

        newest_users = fetch_current_ldap_users(self.conn, base_dn=self.user_base_dn)
        self.assertEqual(newest_users, [])
