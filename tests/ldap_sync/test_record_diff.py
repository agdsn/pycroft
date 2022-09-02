#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest

from ldap_sync import types
from ldap_sync.action import AddAction, DeleteAction, IdleAction, ModifyAction
from ldap_sync.record import UserRecord, escape_and_normalize_attrs
from ldap_sync.record_diff import diff_records, diff_attributes
from ldap_sync.types import DN


@pytest.fixture(scope="module")
def dn() -> DN:
    return DN("uid=foo")


@pytest.fixture(scope="module")
def record(dn) -> UserRecord:
    return UserRecord(dn=dn, attrs={'mail': 'shizzle'})


def test_record_subtraction_with_none_adds(record):
    difference = diff_records(None, record)
    assert isinstance(difference, AddAction)
    assert difference.record_dn == record.dn
    assert difference.nonempty_attrs.items() <= record.attrs.items()
    assert all((
        not val
        for key, val in record.attrs.items()
        if key not in difference.nonempty_attrs
    ))


def test_none_subtracted_by_record_deletes(record):
    difference = diff_records(record, None)
    assert isinstance(difference, DeleteAction)
    assert difference.record_dn == record.dn


def test_different_dn_raises_typeerror(record):
    with pytest.raises(TypeError, match="different dn"):
        _ = diff_records(UserRecord(dn=DN("notatest"), attrs={}), record)


def test_same_record_subtraction_idles(record):
    difference = diff_records(record, record)
    assert isinstance(difference, IdleAction)


def test_correctly_different_record_modifies(record, dn):
    difference = diff_records(UserRecord(dn=dn, attrs={'mail': ''}), record)
    assert isinstance(difference, ModifyAction)


class TestAttributeDiff:
    @pytest.mark.parametrize("attrs_current, attrs_desired, modifications", [
        ({"gecos": "bar"},
         {"gecos": None},
         {"gecos": []},),
        ({"foo": "bar"},
         {"foo": "bar", "mail": "admin@sci.hub"},
         {"mail": ["admin@sci.hub"]},),
        ({"gecos": "bar", "mail": "admin@sci.hub"},
         {"gecos": "bar", "mail": ""},
         {"mail": []},),
        ({"gecos": "baz", "mail": "admin@sci.hub"},
         {"gecos":  "bar", "mail": "admin@sci.hub"},
         {"gecos": ["bar"]},),
    ])
    def test_modify_action(
        self,
        dn,
        attrs_current: types.NormalizedAttributes,
        attrs_desired: types.NormalizedAttributes,
        modifications: types.NormalizedAttributes,
    ):
        assert (
            diff_attributes(
                desired_attrs=escape_and_normalize_attrs(attrs_desired),
                current_attrs=escape_and_normalize_attrs(attrs_current),
            )
            == modifications
        )