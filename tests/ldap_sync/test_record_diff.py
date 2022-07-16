#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
import pytest

from ldap_sync.action import AddAction, DeleteAction, IdleAction, ModifyAction
from ldap_sync.record import UserRecord
from ldap_sync.record_diff import diff_records
from ldap_sync.types import DN


@pytest.fixture(scope="module")
def record():
    return UserRecord(dn=DN("test"), attrs={'mail': 'shizzle'})


def test_record_subtraction_with_none_adds(record):
    difference = diff_records(None, record)
    assert isinstance(difference, AddAction)
    assert difference.record == record


def test_none_subtracted_by_record_deletes(record):
    difference = diff_records(record, None)
    assert isinstance(difference, DeleteAction)
    assert difference.record_dn == record.dn


def test_different_dn_raises_typeerror(record):
    with pytest.raises(TypeError):
        # pylint: disable=expression-not-assigned
        record - UserRecord(dn=DN("notatest"), attrs={})


def test_same_record_subtraction_idles(record):
    difference = diff_records(record, record)
    assert isinstance(difference, IdleAction)


def test_correctly_different_record_modifies(record):
    difference = diff_records(UserRecord(dn=DN("test"), attrs={'mail': ''}), record)
    assert isinstance(difference, ModifyAction)
