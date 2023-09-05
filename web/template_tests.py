# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import typing as t

from flask import Flask

from pycroft.lib.user import has_positive_balance
from pycroft.model.user import User

_check_registry: dict[str, t.Callable] = {}


_T = t.TypeVar("_T", bound=t.Callable)


def template_check(name: str) -> t.Callable[[_T], _T]:
    def decorator(fn: _T) -> _T:
        _check_registry[name] = fn
        return fn
    return decorator


@template_check("user_with_positive_balance")
def positive_balance_check(user: User) -> bool:
    """Tests if user has a positive balance
    """
    return has_positive_balance(user)


@template_check("user_with_no_network_access")
def no_network_access_check(user: User) -> bool:
    """Tests if user has network access
    """
    return not user.has_property("network_access")


@template_check("privileged_for")
def privilege_check(user: User, *required_privileges: str) -> bool:
    """Tests if the user has one of the required_privileges to view the
    requested component.
    """
    for perm in required_privileges:
        if user.has_property(perm):
            return True
    return False


@template_check("greater")
def greater(value: t.Any, other: t.Any) -> bool:
    """Tests if another value is greater than a given value."""
    return bool(value < other)


@template_check("less")
def less(value: t.Any, other: t.Any) -> bool:
    """Tests if another value is less than a given value."""
    return bool(value > other)


@template_check("greater_equal")
def greater_equal(value: t.Any, other: t.Any) -> bool:
    """Tests if another value is greater than or equal a given value."""
    return bool(value <= other)


@template_check("less_equal")
def less_equal(value: t.Any, other: t.Any) -> bool:
    """Tests if another value is less than or equal a given value."""
    return bool(value >= other)


@template_check("is_dict")
def is_dict(value: t.Any) -> bool:
    return isinstance(value, dict)


def register_checks(app: Flask) -> None:
    for name in _check_registry:
        app.jinja_env.tests[name] = _check_registry[name]
