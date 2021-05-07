from unittest import TestCase

import ldap3
import pytest

from ldap_sync.action import Action, IdleAction, AddAction, ModifyAction, DeleteAction
from ldap_sync.record import UserRecord, dn_from_username


class TestActionSubclass:
    def test_instantiation_fails(self):
        with pytest.raises(TypeError):
            Action(record=None)

    def test_subclassing_with_execute_works(self):
        class A(Action):
            def execute(self, **kwargs):
                pass
        try:
            A(record=None)
        except TypeError as e:
            pytest.fail(f"Subclassing raised Exception {e}")


class TestModifyActionConstructor:
    def test_desired_record_passed(self):
        desired = UserRecord(dn=None, attrs={'gecos': 'test'})
        current = UserRecord(dn=None, attrs={})
        action = ModifyAction.from_two_records(desired_record=desired, current_record=current)
        assert action.record == desired

    @pytest.mark.parametrize('attrs_current, attrs_desired, modifications', [
        ({'gecos': 'bar'},
         {'gecos': None},
         {'gecos': []},),
        ({'foo': 'bar'},
         {'foo': 'bar', 'mail': 'admin@sci.hub'},
         {'mail': ['admin@sci.hub']},),
        ({'gecos': 'bar', 'mail': 'admin@sci.hub'},
         {'gecos': 'bar', 'mail': ''},
         {'mail': []},),
        ({'gecos': 'baz', 'mail': 'admin@sci.hub'},
         {'gecos':  'bar', 'mail': 'admin@sci.hub'},
         {'gecos': ['bar']},),
    ])
    def test_modify_action(self, attrs_current, attrs_desired, modifications):
        action = ModifyAction.from_two_records(
            desired_record=UserRecord(dn=None, attrs=attrs_desired),
            current_record=UserRecord(dn=None, attrs=attrs_current)
        )
        assert action.modifications == modifications


def validate_attribute_type(key, value):
    """Validate if some attribute value has the correct type.

    This concerns the single-valuedness, which is estimated using
    a hard-coded, global list :py:obj:`SINGLE_VALUED_ATTRIBUTES`
    capturing teh most relevant attributes restricted to a single
    value.
    """
    if key in SINGLE_VALUED_ATTRIBUTES and isinstance(value, list):
        raise ValueError(f"Value '{value}' for key '{key}' should be a single value")
    if key not in SINGLE_VALUED_ATTRIBUTES and not isinstance(value, list):
        raise ValueError(f"Value '{value}' for key '{key}' should be a list")


@pytest.fixture(scope='class')
def connection():
    server = ldap3.Server('fake_server', get_info=ldap3.ALL)
    connection = ldap3.Connection(server, user='cn=test', password='pw',
                                  client_strategy=ldap3.MOCK_SYNC)
    connection.open()
    yield connection
    connection.strategy.close()


@pytest.fixture(scope='session')
def base():
    return 'ou=Nutzer,ou=Pycroft,dc=AG DSN,dc=de'


@pytest.fixture(scope='session')
def uid():
    return 'shizzle'


@pytest.fixture(scope='session')
def dn(uid, base):
    return dn_from_username(uid, base=base)


class MockedLdapTestBase:
    base = 'ou=Nutzer,ou=Pycroft,dc=AG DSN,dc=de'

    def get_all_objects(self, connection):
        connection.search(search_base=self.base, search_filter='(objectclass=*)', attributes='*')
        return connection.response


SINGLE_VALUED_ATTRIBUTES = ['uidNumber', 'gidNumber', 'homeDirectory',
                            'gecos', 'shadowMin', 'shadowMax',
                            'shadowFlag', 'shadowExpire', 'loginShell']


class TestAddAction(MockedLdapTestBase):
    @pytest.fixture(scope='class')
    def attributes(self):
        return {'objectClass': UserRecord.LDAP_OBJECTCLASSES,
                'mail': ['bas'],
                'userPassword': ['$1$dtruiandetnuhgaldrensutrhawtruhs']}


    @pytest.fixture(scope='class')
    def objects(self, connection, attributes, uid, dn):
        """Objects after executing an AddAction"""
        action = AddAction(record=UserRecord(dn=dn, attrs=attributes))
        action.execute(connection)
        return self.get_all_objects(connection)

    def test_dn_correct(self, objects, dn):
        assert objects[0]['dn'] == dn

    def test_correct_uid_in_attributes(self, objects, uid):
        attrs = objects[0]['attributes']
        # uid is not SINGLE VALUE according to schema
        assert attrs['uid'] == [uid]

    def test_correct_objectclasses(self, objects):
        assert objects[0]['attributes']['objectClass'] == UserRecord.LDAP_OBJECTCLASSES

    def test_other_attributes_passed(self, objects, attributes):
        received_attributes = objects[0]['attributes']
        for key, value in attributes.items():
            validate_attribute_type(key=key, value=value)
            assert key in received_attributes
            assert received_attributes[key] == value


class TestDeleteAction(MockedLdapTestBase):
    @pytest.fixture(scope='class')
    def objects(self, dn, connection):
        connection.add(dn, UserRecord.LDAP_OBJECTCLASSES)
        record = UserRecord(dn=dn, attrs={})
        DeleteAction(record=record).execute(connection)
        return self.get_all_objects(connection)

    def test_no_objects(self, objects):
        assert len(objects) == 0


class TestModifyAction(MockedLdapTestBase):
    @pytest.fixture(scope='class')
    def objects(self, dn, connection):
        connection.add(dn, UserRecord.LDAP_OBJECTCLASSES)
        record = UserRecord(dn=dn, attrs={})
        action = ModifyAction(record=record, modifications={'mail': 'new@shizzle.de'})
        action.execute(connection)
        return self.get_all_objects(connection)

    def test_one_object_changed(self, objects):
        assert len(objects) == 1

    def test_mail_changed(self, objects):
        assert objects[0]['attributes']['mail'] == ['new@shizzle.de']


class IdleActionTestCase(TestCase):
    def test_execute_does_nothing(self):
        record = UserRecord(dn='test', attrs={})
        IdleAction(record=record).execute()
