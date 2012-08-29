# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from pycroft.lib.user import has_positive_balance, has_exceeded_traffic

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


@template_check("user_with_no_internet")
def no_internet_check(user):
    """Tests if user has no internet
    """
    return user.has_property("no_internet")


@template_check("user_with_traffic_exceeded")
def exceeded_traffic_check(user):
    """Tests if user has exceeded his traffic
    """
    return has_exceeded_traffic(user)


def register_tests(app):
    for name in _check_registry:
        app.jinja_env.tests[name] = _check_registry[name]
