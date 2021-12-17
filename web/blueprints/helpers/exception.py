import logging
import traceback
from contextlib import contextmanager

from flask import flash
from sqlalchemy.orm import Session

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
def handle_errors(session: Session):
    """Flash a message, roll back the session, and wrap unknown errors in a ``PycroftException``

    :raises PycroftException:
    """
    try:
        yield
    except PycroftException as e:
        flash(exception_flash_message(e), 'error')
        session.rollback()
        raise
    except Exception as e:
        traceback.print_exc()
        flash(f"Es ist ein unerwarteter Fehler aufgetreten: {e}", "error")
        session.rollback()
        raise UnexpectedException from e


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
