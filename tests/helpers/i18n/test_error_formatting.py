import traceback

from pycroft.helpers.i18n import deferred_gettext
from .assertions import assertSimpleMessageCorrect


def get_format_error_message(message, args, kwargs):
    try:
        message.format(*args, **kwargs)
    except (TypeError, ValueError, IndexError, KeyError) as e:
        return ''.join(traceback.format_exception_only(type(e), e))
    else:
        raise AssertionError()


def test_missing_positional_argument():
    message = "{0} {1}"
    args = (1,)
    kwargs = {}
    error = get_format_error_message(message, args, kwargs)
    m = deferred_gettext(message).format(*args)
    text = f'Could not format message "{message}" (args={args}, kwargs={kwargs}): {error}'
    assertSimpleMessageCorrect(m, message, None, args, kwargs, text)


def test_missing_keyword_argument():
    message = "{foo}"
    args = (1,)
    kwargs = {}
    error = get_format_error_message(message, args, kwargs)
    m = deferred_gettext(message).format(*args)
    text = f'Could not format message "{message}" (args={args}, kwargs={kwargs}): {error}'
    assertSimpleMessageCorrect(m, message, None, args, kwargs, text)
