import traceback

from pycroft.helpers.i18n import deferred_gettext
from .assertions import assertSimpleMessageCorrect


def get_format_error_message(message, args, kwargs):
    try:
        message.format(*args, **kwargs)
    except (TypeError, ValueError, IndexError, KeyError) as e:
        return u''.join(traceback.format_exception_only(type(e), e))
    else:
        raise AssertionError()


def test_missing_positional_argument():
    message = u"{0} {1}"
    args = (1,)
    kwargs = {}
    error = get_format_error_message(message, args, kwargs)
    m = deferred_gettext(message).format(*args)
    text = (u'Could not format message "{}" (args={}, kwargs={}): {}'
            .format(message, args, kwargs, error))
    assertSimpleMessageCorrect(m, message, None, args, kwargs, text)


def test_missing_keyword_argument():
    message = u"{foo}"
    args = (1,)
    kwargs = {}
    error = get_format_error_message(message, args, kwargs)
    m = deferred_gettext(message).format(*args)
    text = (u'Could not format message "{}" (args={}, kwargs={}): {}'
            .format(message, args, kwargs, error))
    assertSimpleMessageCorrect(m, message, None, args, kwargs, text)