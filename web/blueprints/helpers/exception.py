import traceback

from flask import flash
from sqlalchemy.exc import InternalError

from pycroft.helpers import AutoNumber
from pycroft.model import session

from pycroft.lib.net import MacExistsException, SubnetFullException
from pycroft.model.host import MulticastFlagException
from pycroft.model.types import InvalidMACAddressException


def web_execute(function, success_message, *args, **kwargs):
    try:
        result = function(*args, **kwargs)

        if success_message:
            flash(success_message, 'success')

        return result, True
    except MacExistsException:
        flash("Die MAC-Adresse ist bereits in Verwendung.", 'error')

        session.session.rollback()
    except SubnetFullException:
        flash("Das IP-Subnetz ist voll.", 'error')

        session.session.rollback()
    except MulticastFlagException:
        flash("Die MAC-Adresse enthält ein aktives Multicast-Bit.", 'error')

        session.session.rollback()
    except InvalidMACAddressException:
        flash("Die MAC-Adresse ist ungültig.", 'error')

        session.session.rollback()
    except InternalError as e:
        # Special case: Username already taken in Abe
        # Should be removed after migration
        if "Username already taken in Abe!" in str(e):
            flash("Dieser Benutzername wird bereits in Abe verwendet.", 'error')

            session.session.rollback()
        else:
            raise e
    except Exception as e:
        traceback.print_exc()
        flash("Es ist ein unerwarteter Fehler aufgetreten: {}".format(e), "error")

    session.session.rollback()

    return None, False
