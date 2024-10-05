#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
"""
ldap_sync.record_diff
~~~~~~~~~~~~~~~~~~~~~
"""
import typing

from .concepts import record, action, types


def diff_attributes(
    current_attrs: types.NormalizedAttributes,
    desired_attrs: types.NormalizedAttributes,
) -> types.NormalizedAttributes:
    """Determine which attributes need to be updated.

    This function doesn't check whether both dicts have equal
    keys, meaning keys not given in :paramref:`desired_attrs`
    won't end up in the modification dict.  Removing attributes
    has to be done by explicitly setting them to an empty string.

    :param current_attrs: the attributes of the entity currently in the system.
    :param desired_attrs: the attributes we want the entity to have.
    """
    return {
        attr: desired_value
        for attr, desired_value in desired_attrs.items()
        if attr not in current_attrs  # attribute is new
        or current_attrs[attr] != desired_value  # attribute has changed
    }


def diff_user_attributes(
    current_attrs: types.NormalizedAttributes,
    desired_attrs: types.NormalizedAttributes,
) -> types.NormalizedAttributes:
    """Like :func:`diff_attributes`, but aware of the
    `ppolicy <https://linux.die.net/man/5/slapo-ppolicy>`_ overlay."""
    modifications = diff_attributes(current_attrs, desired_attrs)
    # Do not try to delete pwdAccountLockedTime if password is changed,
    # as the ppolicy overlay already takes care of that.
    password_changed = "userPassword" in modifications
    locked_time_present_or_none = not modifications.get("pwdAccountLockedTime")
    if password_changed and locked_time_present_or_none:
        modifications.pop("pwdAccountLockedTime", None)
    return modifications


def diff_records[T: record.Record](current: T | None, desired: T | None) -> action.Action:
    """Determines an action to take, given a desired and a current record.

    :param current: the present state
    :param desired: the future state
    """
    match (current, desired):
        case (None, None):
            raise ValueError("cannot diff two nonexistent records")
        case (None, desired):
            return action.AddAction(record=desired)
        case (current, None):
            return action.DeleteAction(record_dn=current.dn)
        case (c, d) if c == d:
            return action.IdleAction(record_dn=d.dn)
        case (record.Record(dn=dn1), record.Record(dn=dn2)) if dn1 != dn2:
            raise TypeError("Cannot compute difference between records of different dn")
        case (record.UserRecord() as c, record.UserRecord() as d):
            return action.ModifyAction(
                record_dn=d.dn, modifications=diff_user_attributes(c.attrs, d.attrs)
            )
        case (record.GroupRecord() as c, record.GroupRecord() as d):
            return action.ModifyAction(
                record_dn=d.dn, modifications=diff_attributes(c.attrs, d.attrs)
            )
        case (c, d):
            raise TypeError(f"Cannot diff {type(c).__name__} and {type(d).__name__}")
    # see https://github.com/python/mypy/issues/12534
    raise AssertionError  # pragma: no cover


def iter_zip_dicts[
    TKey, TVal1, TVal2
](
    d1: dict[TKey, TVal1],
    d2: dict[TKey, TVal2],
) -> typing.Iterator[tuple[TKey, tuple[TVal1 | None, TVal2 | None]]]:
    for k in d1.keys() | d2.keys():
        yield k, (d1.get(k), d2.get(k))


def bulk_diff_records(
    current: typing.Iterable[record.Record], desired: typing.Iterable[record.Record]
) -> dict[types.DN, action.Action]:
    return {
        dn: diff_records(cur, des)
        for dn, (cur, des) in iter_zip_dicts(
            {r.dn: r for r in current},
            {r.dn: r for r in desired},
        )
    }
