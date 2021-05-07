import pytest

from ldap_sync.action import Action, IdleAction, AddAction, ModifyAction, DeleteAction
from ldap_sync.record import UserRecord
from . import validate_attribute_type, get_all_objects


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
        DeleteAction(record=record).execute(connection)
        return get_all_objects(connection, base)

    def test_no_objects(self, objects):
        assert len(objects) == 0


class TestModifyAction:
    @pytest.fixture(scope='class')
    def objects(self, dn, connection, base):
        connection.add(dn, UserRecord.LDAP_OBJECTCLASSES)
        record = UserRecord(dn=dn, attrs={})
        action = ModifyAction(record=record, modifications={'mail': 'new@shizzle.de'})
        action.execute(connection)
        return get_all_objects(connection, base)

    def test_one_object_changed(self, objects):
        assert len(objects) == 1

    def test_mail_changed(self, objects):
        assert objects[0]['attributes']['mail'] == ['new@shizzle.de']


def test_execute_does_nothing():
    IdleAction(record=(UserRecord(dn='test', attrs={}))).execute()
