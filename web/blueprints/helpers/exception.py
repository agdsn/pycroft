import logging
import traceback
import typing as t
from contextlib import contextmanager

from flask import flash, abort, make_response
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import Session, SessionTransaction

from pycroft.exc import PycroftException
from pycroft.lib.net import MacExistsException, SubnetFullException
from pycroft.model import session
from pycroft.model.host import MulticastFlagException
from pycroft.model.types import InvalidMACAddressException


logger = logging.getLogger('web.exc')


def web_execute(function, success_message, *args, **kwargs):
    from warnings import warn
    warn("Use `handle_errors` context manager instead.", DeprecationWarning)
    try:
        result = function(*args, **kwargs)

        if success_message:
            flash(success_message, 'success')

        return result, True
    except PycroftException as e:
        flash(exception_flash_message(e), 'error')
        session.session.rollback()
    except Exception as e:
        traceback.print_exc()
        flash(f"Es ist ein unerwarteter Fehler aufgetreten: {e}", "error")

    session.session.rollback()

    return None, False


class UnexpectedException(PycroftException):
    pass


@contextmanager
def flash_and_wrap_errors() -> t.Iterator[None]:
    """Flash a message, roll back the session, and wrap unknown errors in a ``PycroftException``

    :raises PycroftException:
    """
    try:
        yield
    except PycroftException as e:
        flash(exception_flash_message(e), 'error')
        raise
    except Exception as e:
        traceback.print_exc()
        logger.exception("Unexpected error when handling web response", stack_info=True)
        flash(f"Es ist ein unerwarteter Fehler aufgetreten: {e}", "error")
        raise UnexpectedException from e


@contextmanager
# TODO rename to „wrap_errors“; `handle` suggests „I'll deal with everything“, which is incorrect
def handle_errors(
    error_response: t.Callable[[], ResponseReturnValue] | None = None,
) -> t.Iterator[SessionTransaction]:
    """Wraps errors as `PycroftErrors` and turns them into a flash message.

    Example:

        def default_response(): return render_template("template.html")

        with handle_errors(error_response=default_response), session.begin_nested():
            ... # call some `lib` functions
        session.commit()

    :param error_response: if given, this will be called when a `PycroftException` is caught
        and the return value is used as the response via :py:function:`flask.abort`.
    """
    cm = flash_and_wrap_errors()

    if error_response is None:
        with cm as n:
            yield n
        return

    try:
        with cm as n:
            yield n
    except PycroftException:
        abort(make_response(error_response()))


def exception_flash_message(e: PycroftException) -> str:
    match e:
        case MacExistsException():
            return "Die MAC-Adresse ist bereits in Verwendung."
        case SubnetFullException():
            return "Das IP-Subnetz ist voll."
        case MulticastFlagException():
            return "Die MAC-Adresse enthält ein aktives Multicast-Bit."
        case InvalidMACAddressException():
            return "Die MAC-Adresse ist ungültig."
        case _:
            logger.warning("No flash message known for exception type %s", type(e), exc_info=True)
            return f"Es ist ein Fehler aufgetreten: {e}"
