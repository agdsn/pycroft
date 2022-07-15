#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

import typing

from . import action, record, types


T = typing.TypeVar("T", bound="record.Record")


def diff_attributes(
    current_attrs: types.NormalizedAttributes,
    desired_attrs: types.NormalizedAttributes,
) -> types.NormalizedAttributes:
    """Determine which attributes need to be updated.

    This function doesn't check whether both dicts have equal
    keys, meaning keys not given in :paramref:`desired_attrs`
    won't end up in the modification dict.  Removing attributes
    has to be done by explicitly setting them to an empty string.
    """
    updated_attrs = desired_attrs
    for key, old_value in current_attrs.items():
        if key not in updated_attrs:
            continue
        if old_value == updated_attrs[key]:
            # we don't need to execute anupdate if the value doesn't change
            updated_attrs.pop(key)
    return updated_attrs


def diff_user_attributes(
    current_attrs: types.NormalizedAttributes,
    desired_attrs: types.NormalizedAttributes,
) -> types.NormalizedAttributes:
    modifications = diff_attributes(current_attrs, desired_attrs)
    # Do not try to delete pwdAccountLockedTime if password is changed,
    # as the ppolicy overlay already takes care of that.
    password_changed = "userPassword" in modifications
    locked_time_present_or_none = not modifications.get("pwdAccountLockedTime")
    if password_changed and locked_time_present_or_none:
        modifications.pop("pwdAccountLockedTime", None)
    return modifications


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
            return action.ModifyAction(
                record=d, modifications=diff_user_attributes(c.attrs, d.attrs)
            )
        case (record.GroupRecord() as c, record.GroupRecord() as d):
            return action.ModifyAction(
                record=d, modifications=diff_attributes(c.attrs, d.attrs)
            )
        case (c, d):
            raise TypeError(f"Cannot diff {type(c).__name__} and {type(d).__name__}")
