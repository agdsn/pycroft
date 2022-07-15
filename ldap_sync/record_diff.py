#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing

from . import action, record


T = typing.TypeVar("T", bound="record.Record")


def modify_from_records(current_record: T, desired_record: T) -> action.ModifyAction:
    """Construct a ModifyAction from two records.

    This method doesn't check whether the dn is equal, it only
    acesses ``record.attrs``, respectively.

    This method also doesn't check whether both dicts have equal
    keys, meaning keys not given in :param:`desired_record.attrs`
    won't end up in the modification dict.  Removing attributes
    has to be done by explicitly setting them to an empty string.
    """
    current_attrs = current_record.attrs
    updated_attrs = desired_record.attrs
    for key, old_value in current_attrs.items():
        if key not in updated_attrs:
            continue
        if old_value == updated_attrs[key]:
            # we don't need to execute anupdate if the value doesn't change
            updated_attrs.pop(key)

    return action.ModifyAction(record=desired_record, modifications=updated_attrs)


def diff_records(desired: T | None, current: T | None) -> action.Action:
    match (current, desired):
        case (None, None):
            raise ValueError("cannot diff two nonexistent records")
        case (None, desired):
            return action.AddAction(record=desired)
        case (current, None):
            return action.DeleteAction(record=current)
        case (c, d) if c == d:
            return action.IdleAction(record=d)
        case (record.Record(dn=dn1), record.Record(dn=dn2)) if dn1 != dn2:
            raise TypeError("Cannot compute difference between records of different dn")
        case (record.UserRecord() as c, record.UserRecord() as d):
            a = modify_from_records(desired_record=d, current_record=c)
            # Do not try to delete pwdAccountLockedTime if password is changed,
            # as the ppolicy overlay already takes care of that.
            password_changed = 'userPassword' in a.modifications
            locked_time_present_or_none = not a.modifications.get('pwdAccountLockedTime')
            if password_changed and locked_time_present_or_none:
                a.modifications.pop('pwdAccountLockedTime', None)
            return a
        case (record.GroupRecord() as c, record.GroupRecord() as d):
            return modify_from_records(desired_record=d, current_record=c)
        case (c, d):
            raise TypeError(f"Cannot diff {type(c).__name__} and {type(d).__name__}")
