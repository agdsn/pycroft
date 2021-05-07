from unittest import TestCase

import pytest

from ldap_sync.action import AddAction, DeleteAction, IdleAction, ModifyAction
from ldap_sync.record import UserRecord, RecordState, _canonicalize_to_list


def assertSubDict(subdict, container):
    container_subdict = {k: v for k, v in container.items() if k in subdict}
    if subdict != container_subdict:
        pytest.fail(f"{subdict} not a subdict of {container}")


class TestRecordDirectInit:
    @pytest.fixture(scope='class')
    def record(self):
        return UserRecord(dn='test', attrs={'userPassword': "{CRYPT}**shizzle",
                                            'mail': None, 'cn': "User", 'uid': 50})

    def test_empty_attr_converted_to_list(self, record):
        assertSubDict({'mail': []}, record.attrs)

    def test_nonempty_attr_converted_to_list(self, record):
        assertSubDict({'cn': ["User"]}, record.attrs)

    def test_critical_chars_escaped_and_converted_to_list(self, record):
        assert record.attrs['userPassword'] == ["{CRYPT}\\2a\\2ashizzle"]

    def test_int_attrs_not_converted_to_string(self, record):
        assert record.attrs['uid'] == [50]


class TestRecord:
    @pytest.fixture(scope='class')
    def record(self):
        return UserRecord(dn='test', attrs={'mail': 'shizzle'})

    def test_record_equality(self, record):
        assert record == UserRecord(dn='test', attrs={'mail': 'shizzle'})

    def test_record_noncanonical_equality(self, record):
        assert record == UserRecord(dn='test', attrs={'mail': ['shizzle']})

    def test_record_subtraction_with_none_adds(self, record):
        difference = record - None
        assert isinstance(difference, AddAction)
        assert difference.record == record

    def test_none_subtracted_by_record_deletes(self, record):
        difference = None - record
        assert isinstance(difference, DeleteAction)
        assert difference.record == record

    def test_different_dn_raises_typeerror(self, record):
        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            record - UserRecord(dn='notatest', attrs={})

    def test_same_record_subtraction_idles(self, record):
        difference = record - record
        assert isinstance(difference, IdleAction)

    def test_correctly_different_record_modifies(self, record):
        difference = record - UserRecord(dn='test', attrs={'mail': ''})
        assert isinstance(difference, ModifyAction)

    def test_record_from_ldap_record(self):
        ldapsearch_record = {'dn': 'somedn',
                             'attributes': {'mail': u'mail', 'gecos': u'baz'},
                             'raw_attributes': {'mail': b'mail'}}
        record = UserRecord.from_ldap_record(ldapsearch_record)
        assertSubDict({'mail': [u'mail'], 'gecos': [u'baz']}, record.attrs)
        for key in UserRecord.get_synced_attributes():
            assert key in record.attrs


class TestEmptyAttributeRecord:
    @pytest.fixture(scope='class')
    def record(self):
        return UserRecord(dn='test', attrs={'mail': None})

    def test_attribute_is_empty_list(self, record):
        assert record.attrs['mail'] == []

    def test_empty_attribute_removed(self, record):
        record.remove_empty_attributes()
        assert 'mail' not in record.attrs


class TestRecordFromOrm:
    @pytest.fixture(scope='class')
    def attrs(self):
        class complete_user:
            name = 'foo bar shizzle'
            login = 'shizzle'
            email = 'shizzle@agdsn.de'
            email_forwarded = True

            class unix_account:
                uid = 10006
                gid = 100
                home_directory = '/home/test'
                login_shell = '/bin/bash'
            passwd_hash = 'somehash'

        return UserRecord.from_db_user(complete_user, base_dn='o=test').attrs

    def test_uid_correct(self, attrs):
        assert attrs['uid'] == ['shizzle']

    def test_uidNumber_correct(self, attrs):
        assert attrs['uidNumber'] == [10006]

    def test_gidNumber_correct(self, attrs):
        assert attrs['gidNumber'] == [100]

    def test_homeDirectory_correct(self, attrs):
        assert attrs['homeDirectory'] == ['/home/test']

    def test_userPassword_correct(self, attrs):
        assert attrs['userPassword'] == ['somehash']

    def test_gecos_correct(self, attrs):
        assert attrs['gecos'] == ['foo bar shizzle']

    def test_cn_correct(self, attrs):
        assert attrs['cn'] == ['foo bar shizzle']

    def test_sn_correct(self, attrs):
        assert attrs['sn'] == ['foo bar shizzle']

    def test_mail_correct(self, attrs):
        assert attrs['mail'] == ['shizzle@agdsn.de']


@pytest.mark.parametrize('value, expected', [
    ('', []),
    (None, []),
    (0, [0]),
    ('teststring', ['teststring']),
    (False, [False]),
    ([], []),
    (['l', 'bar', 0, None], ['l', 'bar', 0, None]),
])
def test_canonicalization(value, expected):
    assert _canonicalize_to_list(value) == expected


class TestRecordState:
    @pytest.fixture(scope='class')
    def record(self):
        return UserRecord(dn='test', attrs={})

    def test_equality_both_none(self):
        assert RecordState() == RecordState()

    def test_equality_only_current(self, record):
        assert RecordState(current=record) == RecordState(current=record)

    def test_equality_only_desired(self, record):
        assert RecordState(desired=record) == RecordState(desired=record)

    def test_equality_current_and_desired(self, record):
        assert RecordState(current=record, desired=record) \
            == RecordState(current=record, desired=record)

    def test_not_equal_to_none(self, record):
        assert RecordState() != RecordState(current=record)
