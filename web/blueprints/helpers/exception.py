import logging
import traceback
import typing as t
from contextlib import contextmanager

from flask import flash, abort, make_response
from flask.typing import ResponseReturnValue
from sqlalchemy.orm import SessionTransaction

from pycroft.exc import PycroftException
from pycroft.lib.net import MacExistsException, SubnetFullException
from pycroft.model.host import MulticastFlagException
from pycroft.model.types import InvalidMACAddressException


logger = logging.getLogger('web.exc')


class UnexpectedException(PycroftException):
    pass


def flash_handler(e: PycroftException) -> None:
    flash(exception_flash_message(e), "error")


ErrorHandler = t.Callable[[PycroftException], None]


@contextmanager
def flash_and_wrap_errors(
    handler_map: dict[type[PycroftException], ErrorHandler] | None = None,
) -> t.Iterator[None]:
    """Flash a message, roll back the session, and wrap unknown errors in a ``PycroftException``

    :param handler_map: specifies what to do with exception types.
        The default is to flash a message, but other actions may be desired instead
        (such as appending the error to a form).

    :raises PycroftException:
    """
    try:
        yield
    except PycroftException as e:
        handlers = handler_map or {}
        handler = next(
            (h for type_, h in handlers.items() if isinstance(e, type_)), flash_handler
        )
        handler(e)
        raise
    except Exception as e:
        traceback.print_exc()
        logger.exception("Unexpected error when handling web response", stack_info=True)
        flash(f"Es ist ein unerwarteter Fehler aufgetreten: {e}", "error")
        raise UnexpectedException from e


ErrorHandlerMap = dict[type[PycroftException], ErrorHandler]


@contextmanager
# TODO rename to „wrap_errors“; `handle` suggests „I'll deal with everything“, which is incorrect
def handle_errors(
    error_response: t.Callable[[], ResponseReturnValue]
    | ResponseReturnValue
    | None = None,
    handler_map: ErrorHandlerMap | None = None,
) -> t.Iterator[SessionTransaction]:
    """Wraps errors as `PycroftErrors` and turns them into a flash message.

    Example:

        def default_response(): return render_template("template.html")

        with handle_errors(error_response=default_response), session.begin_nested():
            ... # call some `lib` functions
        session.commit()

    :param error_response: if given, this will be called when a `PycroftException` is caught
        and the return value is used as the response via :py:function:`flask.abort`.
    :param handler_map: specifies what to do with certain exception types.
    """
    cm = flash_and_wrap_errors(handler_map)

    if error_response is None:
        with cm as n:
            yield n
        return

    try:
        with cm as n:
            yield n
    except PycroftException:
        resp = error_response() if callable(error_response) else error_response
        abort(make_response(resp))


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
