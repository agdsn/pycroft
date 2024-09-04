from pycroft.helpers import user as user_helper
from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.logging import log_user_event
from pycroft.model.session import with_transaction
from pycroft.model.user import User

from ._old import can_target



def maybe_setup_wifi(user: User, processor: User) -> str | None:
    """If wifi is available, sets a wifi password."""
    if user.room and user.room.building.wifi_available:
        return reset_wifi_password(user, processor)
    return None


@with_transaction
def change_password(user: User, password: str) -> None:
    # TODO: verify password complexity
    user.password = password

    message = deferred_gettext("Password was changed")
    log_user_event(author=user, user=user, message=message.to_json())


@with_transaction
def reset_password(user: User, processor: User) -> str:
    if not can_target(user, processor):
        raise PermissionError(
            "cannot reset password of a user with a" " greater or equal permission level."
        )

    plain_password = user_helper.generate_password(12)
    user.password = plain_password

    message = deferred_gettext("Password was reset")
    log_user_event(author=processor, user=user, message=message.to_json())

    return plain_password


@with_transaction
def reset_wifi_password(user: User, processor: User) -> str:
    plain_password = generate_wifi_password()
    user.wifi_password = plain_password

    message = deferred_gettext("WIFI-Password was reset")
    log_user_event(author=processor, user=user, message=message.to_json())

    return plain_password


@with_transaction
def change_password_from_token(token: str | None, password: str) -> bool:
    if token is None:
        return False

    user = User.q.filter_by(password_reset_token=token).one_or_none()

    if user:
        change_password(user, password)
        user.password_reset_token = None
        user.email_confirmed = True

        return True
    else:
        return False


def generate_wifi_password() -> str:
    return user_helper.generate_password(12)
