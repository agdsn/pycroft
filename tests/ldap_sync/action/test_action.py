import typing

import pytest

from ldap_sync.action import Action, IdleAction, AddAction, ModifyAction, DeleteAction
from ldap_sync.record_diff import diff_records, diff_attributes
from ldap_sync.record import UserRecord
from . import validate_attribute_type, get_all_objects


class TestActionSubclass:
    def test_instantiation_fails(self, dn):
        with pytest.raises(TypeError):
            Action(record_dn=dn)

    def test_subclassing_with_execute_works(self, dn):
        class A(Action):
            def execute(self, **kwargs):
                pass
        try:
            A(record_dn=dn)
        except TypeError as e:
            pytest.fail(f"Subclassing raised Exception {e}")


class TestModifyActionConstructor:
    def test_desired_record_passed(self, dn):
        desired = UserRecord(dn=dn, attrs={'gecos': 'test'})
        current = UserRecord(dn=dn, attrs={})
        action = typing.cast(ModifyAction, diff_records(current=current, desired=desired))
        assert action.record_dn == desired.dn
        assert action.modifications == {'gecos': ['test']}

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
    def test_modify_action(self, dn, attrs_current, attrs_desired, modifications):
        # TODO expand these tests a lot && move to `test_diff`
        # pass it through UserRecord for normalization of attributes
        current = UserRecord(dn=dn, attrs=attrs_current)
        desired = UserRecord(dn=dn, attrs=attrs_desired)
        assert current.attrs['uidNumber'] == []  # litmus test for user-relative normalization
        assert (
            diff_attributes(desired_attrs=desired.attrs, current_attrs=current.attrs)
            == modifications
        )


class TestAddAction:
    @pytest.fixture(scope='class')
    def attributes(self):
        return {'objectClass': UserRecord.LDAP_OBJECTCLASSES,
                'mail': ['bas'],
                'userPassword': ['$1$dtruiandetnuhgaldrensutrhawtruhs']}


    @pytest.fixture(scope='class')
    def objects(self, connection, attributes, uid, dn, base):
        """Objects after executing an AddAction"""
        action = AddAction(record=UserRecord(dn=dn, attrs=attributes))
        action.execute(connection)
        return get_all_objects(connection, base)

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


class TestDeleteAction:
    @pytest.fixture(scope='class')
    def objects(self, dn, connection, base):
        connection.add(dn, UserRecord.LDAP_OBJECTCLASSES)
        record = UserRecord(dn=dn, attrs={})
        DeleteAction(record_dn=record.dn).execute(connection)
        return get_all_objects(connection, base)

    def test_no_objects(self, objects):
        assert len(objects) == 0


class TestModifyAction:
    @pytest.fixture(scope='class')
    def objects(self, dn, connection: ldap3.Connection, base):
        connection.add(dn, UserRecord.LDAP_OBJECTCLASSES)
        record = UserRecord(dn=dn, attrs={})
        action = ModifyAction(record_dn=record.dn, modifications={'mail': 'new@shizzle.de'})
        action.execute(connection)
        return get_all_objects(connection, base)

    def test_one_object_changed(self, objects):
        assert len(objects) == 1

    def test_mail_changed(self, objects):
        assert objects[0]['attributes']['mail'] == ['new@shizzle.de']


def test_execute_does_nothing():
    record = UserRecord(dn='test', attrs={})
    IdleAction(record_dn=record.dn).execute()
