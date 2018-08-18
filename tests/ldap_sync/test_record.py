from unittest import TestCase as TestCase_

from ldap_sync.record import Record, RecordState, _canonicalize_to_list
from ldap_sync.action import AddAction, DeleteAction, IdleAction, ModifyAction


class TestCase(TestCase_):
    def assertSubDict(self, subdict, container):
        container_subdict = {k: v for k, v in container.items() if k in subdict}
        if subdict != container_subdict:
            self.fail("{} not a subdict of {}".format(subdict, container))


class RecordDirectInitTestCase(TestCase):
    def setUp(self):
        self.record = Record(dn='test', attrs={'userPassword': "{CRYPT}**shizzle",
                                               'mail': None, 'cn': "User", 'uid': 50})

    def test_empty_attr_converted_to_list(self):
        self.assertSubDict({'mail': []}, self.record.attrs)

    def test_nonempty_attr_converted_to_list(self):
        self.assertSubDict({'cn': ["User"]}, self.record.attrs)

    def test_critical_chars_escaped_and_converted_to_list(self):
        self.assertEqual(self.record.attrs['userPassword'], ["{CRYPT}\\2a\\2ashizzle"])

    def test_int_attrs_not_converted_to_string(self):
        self.assertEqual(self.record.attrs['uid'], [50])


class RecordTestCase(TestCase):
    def setUp(self):
        self.record = Record(dn='test', attrs={'mail': 'shizzle'})

    def test_record_equality(self):
        self.assertEqual(self.record, Record(dn='test', attrs={'mail': 'shizzle'}))

    def test_record_noncanonical_equality(self):
        self.assertEqual(self.record, Record(dn='test', attrs={'mail': ['shizzle']}))

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
        difference = self.record - Record(dn='test', attrs={'mail': ''})
        self.assertIsInstance(difference, ModifyAction)

    def test_record_from_ldap_record(self):
        ldapsearch_record = {'dn': 'somedn',
                             'attributes': {'mail': u'mail', 'gecos': u'baz'},
                             'raw_attributes': {'mail': b'mail'}}
        record = Record.from_ldap_record(ldapsearch_record)
        self.assertSubDict({'mail': [u'mail'], 'gecos': [u'baz']}, record.attrs)
        for key in Record.SYNCED_ATTRIBUTES:
            self.assertIn(key, record.attrs)


class EmptyAttributeRecordTestCase(TestCase):
    def setUp(self):
        self.record = Record(dn='test', attrs={'mail': None})

    def test_attribute_is_empty_list(self):
        self.assertEqual(self.record.attrs['mail'], [])

    def test_empty_attribute_removed(self):
        self.record.remove_empty_attributes()
        self.assertNotIn('mail', self.record.attrs)


class RecordFromOrmTestCase(TestCase):
    class complete_user(object):
        name = 'foo bar shizzle'
        login = 'shizzle'
        email = 'shizzle@agdsn.de'
        class unix_account(object):
            uid = 10006
            gid = 100
            home_directory = '/home/test'
            login_shell = '/bin/bash'
        passwd_hash = 'somehash'

    def setUp(self):
        self.attrs = Record.from_db_user(self.complete_user, base_dn='o=test').attrs

    def test_attributes_passed(self):
        pass

    def test_uid_correct(self):
        self.assertEqual(self.attrs['uid'], ['shizzle'])

    def test_uidNumber_correct(self):
        self.assertEqual(self.attrs['uidNumber'], [10006])

    def test_gidNumber_correct(self):
        self.assertEqual(self.attrs['gidNumber'], [100])

    def test_homeDirectory_correct(self):
        self.assertEqual(self.attrs['homeDirectory'], ['/home/test'])

    def test_userPassword_correct(self):
        self.assertEqual(self.attrs['userPassword'], ['somehash'])

    def test_gecos_correct(self):
        self.assertEqual(self.attrs['gecos'], ['foo bar shizzle'])

    def test_cn_correct(self):
        self.assertEqual(self.attrs['cn'], ['foo bar shizzle'])

    def test_sn_correct(self):
        self.assertEqual(self.attrs['sn'], ['foo bar shizzle'])

    def test_mail_correct(self):
        self.assertEqual(self.attrs['mail'], ['shizzle@agdsn.de'])


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
