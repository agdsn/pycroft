import datetime

from pycroft.helpers.i18n.deferred import deferred_gettext, deferred_dgettext
from pycroft.helpers.i18n.formatting import format_datetime
from .assertions import assertSimpleMessageCorrect


def test_simple():
    message = "test"
    m = deferred_gettext(message)
    assertSimpleMessageCorrect(m, message, None, (), {}, message)


def test_simple_with_domain():
    message = "test"
    domain = "domain"
    m = deferred_dgettext(domain, message)
    assertSimpleMessageCorrect(m, message, domain, (), {}, message)


def test_simple_format_args():
    message = "test {} at {}"
    arg1 = "arg1"
    arg2 = datetime.datetime.utcnow()
    m = deferred_gettext(message).format(arg1, arg2)
    expected_result = message.format(arg1, format_datetime(arg2))
    assertSimpleMessageCorrect(m, message,
                               None, (arg1, arg2), {}, expected_result)


def test_simple_format_kwargs():
    message = "test {arg1} at {arg2}"
    arg1 = "arg1"
    arg2 = datetime.datetime.utcnow()
    m = deferred_gettext(message).format(arg1=arg1, arg2=arg2)
    expected_result = message.format(arg1=arg1, arg2=format_datetime(arg2))
    assertSimpleMessageCorrect(m, message,
                               None, (), {"arg1": arg1, "arg2": arg2}, expected_result)
