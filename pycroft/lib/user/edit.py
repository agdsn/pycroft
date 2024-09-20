from datetime import date


from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.address import get_or_create_address
from pycroft.lib.logging import log_user_event
from pycroft.model.session import with_transaction
from pycroft.model.user import User

from .mail import send_confirmation_email
from .permission import can_target


@with_transaction
def edit_name(user: User, name: str, processor: User) -> User:
    """Changes the name of the user and creates a log entry.

    :param user: The user object.
    :param name: The new full name.
    :return: The changed user object.
    """

    if not name:
        raise ValueError()

    if name == user.name:
        # name wasn't changed, do nothing
        return user

    old_name = user.name
    user.name = name
    message = deferred_gettext("Changed name from {} to {}.")
    log_user_event(author=processor, user=user, message=message.format(old_name, name).to_json())
    return user


@with_transaction
def edit_email(
    user: User,
    email: str | None,
    email_forwarded: bool,
    processor: User,
    is_confirmed: bool = False,
) -> User:
    """
    Changes the email address of a user and creates a log entry.

    :param user: User object to change
    :param email: New email address (empty interpreted as ``None``)
    :param email_forwarded: Boolean if emails should be forwarded
    :param processor: User object of the processor, which issues the change
    :param is_confirmed: If the email address is already confirmed
    :return: Changed user object
    """

    if not can_target(user, processor):
        raise PermissionError(
            "cannot change email of a user with a" " greater or equal permission level."
        )

    if not email:
        email = None
    else:
        email = email.lower()

    if email_forwarded != user.email_forwarded:
        user.email_forwarded = email_forwarded

        log_user_event(
            author=processor,
            user=user,
            message=deferred_gettext("Set e-mail forwarding to {}.")
            .format(email_forwarded)
            .to_json(),
        )

    if is_confirmed:
        user.email_confirmed = True
        user.email_confirmation_key = None

    if email == user.email:
        # email wasn't changed, do nothing
        return user

    old_email = user.email
    user.email = email

    if email is not None:
        if not is_confirmed:
            send_confirmation_email(user)
    else:
        user.email_confirmed = False
        user.email_confirmation_key = None

    message = deferred_gettext("Changed e-mail from {} to {}.")
    log_user_event(author=processor, user=user, message=message.format(old_email, email).to_json())
    return user


@with_transaction
def edit_birthdate(user: User, birthdate: date, processor: User) -> User:
    """
    Changes the birthdate of a user and creates a log entry.

    :param user: User object to change
    :param birthdate: New birthdate
    :param processor: User object of the processor, which issues the change
    :return: Changed user object
    """

    if not birthdate:
        birthdate = None

    if birthdate == user.birthdate:
        # birthdate wasn't changed, do nothing
        return user

    old_bd = user.birthdate
    user.birthdate = birthdate
    message = deferred_gettext("Changed birthdate from {} to {}.")
    log_user_event(author=processor, user=user, message=message.format(old_bd, birthdate).to_json())
    return user


@with_transaction
def edit_person_id(user: User, person_id: int, processor: User) -> User:
    """
    Changes the swdd_person_id of the user and creates a log entry.

    :param user: The user object.
    :param person_id: The new person_id.
    :return: The changed user object.
    """

    if person_id == user.swdd_person_id:
        # name wasn't changed, do nothing
        return user

    old_person_id = user.swdd_person_id
    user.swdd_person_id = person_id
    message = deferred_gettext("Changed tenant number from {} to {}.")
    log_user_event(
        author=processor,
        user=user,
        message=message.format(str(old_person_id), str(person_id)).to_json(),
    )

    return user


@with_transaction
def edit_address(
    user: User,
    processor: User,
    street: str,
    number: str,
    addition: str | None,
    zip_code: str,
    city: str | None,
    state: str | None,
    country: str | None,
) -> None:
    """Changes the address of a user and appends a log entry.

    Should do nothing if the user already has an address.
    """
    address = get_or_create_address(street, number, addition, zip_code, city, state, country)
    user.address = address
    log_user_event(
        deferred_gettext("Changed address to {address}").format(address=str(address)).to_json(),
        processor,
        user,
    )
