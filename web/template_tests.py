# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from pycroft.lib.user import has_positive_balance

_check_registry = {}


def template_check(name):
    def decorator(fn):
        _check_registry[name] = fn
        return fn
    return decorator


@template_check("user_with_positive_balance")
def positive_balance_check(user):
    """Tests if user has a positive balance
    """
    return has_positive_balance(user)


@template_check("user_with_no_network_access")
def no_network_access_check(user):
    """Tests if user has network access
    """
    return not user.has_property("network_access")


@template_check("user_with_traffic_exceeded")
def exceeded_traffic_check(user):
    """Tests if user has exceeded his traffic
    """
    return user.current_credit < 0

@template_check("privileged_for")
def privilege_check(user, *required_privileges):
    """Tests if the user has one of the required_privileges to view the
    requested component.
    """
    for perm in required_privileges:
        if user.has_property(perm):
            return True
    return False


@template_check("greater")
def greater(value, other):
    """Tests if another value is greater than a given value."""
    return value < other


@template_check("less")
def less(value, other):
    """Tests if another value is less than a given value."""
    return value > other


@template_check("greater_equal")
def greater_equal(value, other):
    """Tests if another value is greater than or equal a given value."""
    return value <= other


@template_check("less_equal")
def less_equal(value, other):
    """Tests if another value is less than or equal a given value."""
    return value >= other


@template_check("is_dict")
def is_dict(value):
    return isinstance(value, dict)


def register_checks(app):
    for name in _check_registry:
        app.jinja_env.tests[name] = _check_registry[name]
