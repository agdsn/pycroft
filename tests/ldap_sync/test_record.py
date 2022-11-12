import typing

import pytest
from ldap_sync.concepts import types
from ldap_sync.conversion import ldap_user_to_record

from ldap_sync.concepts.record import (
    UserRecord,
    RecordState,
    _canonicalize_to_list,
    Record,
)
from ldap_sync.concepts.types import DN, LdapRecord


def assertSubDict(subdict, container):
    container_subdict = {k: v for k, v in container.items() if k in subdict}
    if subdict != container_subdict:
        pytest.fail(f"{subdict} not a subdict of {container}")  # pragma: no cover


class TestRecordSubclassing:
    def test_subclassing_without_attributes_fails(self):
        with pytest.raises(TypeError, match="SYNCED_ATTRIBUTES"):
            class _(Record):
                ...

    def test_subclassing_with_attributes_works(self):
        try:
            class _(Record):
                SYNCED_ATTRIBUTES = frozenset({})
        except TypeError:
            pytest.fail("Subclassing failed")  # pragma: no cover


class TestRecordDirectInit:
    @pytest.fixture(scope='class')
    def record(self):
        return UserRecord(dn=DN("test"), attrs={'userPassword': "{CRYPT}**shizzle",
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
        return UserRecord(dn=DN("test"), attrs={'mail': 'shizzle'})

    def test_record_equality(self, record):
        assert record == UserRecord(dn=DN("test"), attrs={'mail': 'shizzle'})

    def test_record_noncanonical_equality(self, record):
        assert record == UserRecord(dn=DN("test"), attrs={'mail': ['shizzle']})

    def test_record_attribute_access(self, record):
        assert record["mail"] == ["shizzle"]

    def test_record_from_ldap_record(self):
        ldapsearch_record: LdapRecord = {
            "dn": DN("somedn"),
            "attributes": {"mail": "mail", "gecos": "baz"},
            "raw_attributes": {"mail": [b"mail"]}
        }
        record = ldap_user_to_record(ldapsearch_record)
        assertSubDict({'mail': ['mail'], 'gecos': ['baz']}, record.attrs)
        for key in UserRecord.get_synced_attributes():
            assert key in record.attrs

class TestRecordValidation:
    @pytest.fixture(scope='class')
    def validate(self) -> typing.Callable[[types.Attributes], None]:
        class RecordWithOneSyncedAttribute(Record):
            SYNCED_ATTRIBUTES = frozenset({"a"})

        return RecordWithOneSyncedAttribute._validate_attributes

    def test_valid_attributes_dict(self, validate):
        validate({"a": "foo"})

    def test_missing_attribute(self, validate):
        with pytest.raises(AssertionError, match="Missing attributes: .*{'a'}"):
            validate({})

    def test_superfluous_attribute(self, validate):
        with pytest.raises(AssertionError, match="Superfluous attributes: .*{'b'}"):
            validate({"a": 1, "b": 5})


class TestEmptyAttributeRecord:
    @pytest.fixture(scope='class')
    def record(self):
        return UserRecord(dn=DN("test"), attrs={'mail': None})

    def test_attribute_is_empty_list(self, record):
        assert record.attrs['mail'] == []


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
        return UserRecord(dn=DN("test"), attrs={})

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
