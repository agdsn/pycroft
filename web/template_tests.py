# -*- coding: utf-8 -*-

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
    return not user.has_property("internet")


@template_check("user_with_traffic_exceeded")
def exceeded_traffic_check(user):
    """Tests if user has exceeded his traffic
    """
    return has_exceeded_traffic(user)

@template_check("privileged_for")
def privilege_check(user, *required_privileges):
    """Tests if the user has one of the required_privileges to view the
    requested component.
    """
    for perm in required_privileges:
        if user.has_property(perm):
            return True
    return False

def register_checks(app):
    for name in _check_registry:
        app.jinja_env.tests[name] = _check_registry[name]