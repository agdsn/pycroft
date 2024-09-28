import typing as t
from datetime import timedelta

from pycroft import config
from pycroft.helpers.printing import generate_user_sheet as generate_pdf
from pycroft.model import session
from pycroft.model.webstorage import WebStorage
from pycroft.model.user import User

from .user_id import encode_type2_user_id


def store_user_sheet(
    new_user: bool,
    wifi: bool,
    user: User,
    timeout: int = 15,
    plain_user_password: str | None = None,
    generation_purpose: str = "",
    plain_wifi_password: str = "",
) -> WebStorage:
    """Generate a user sheet and store it in the WebStorage.

    Returns the generated :class:`WebStorage <pycroft.model.WebStorage>` object holding the pdf.

    :param new_user: generate page with user details
    :param wifi: generate page with wifi credantials
    :param user: A pycroft user. Necessary in every case
    :param timeout: The lifetime in minutes
    :param plain_user_password: Only necessary if ``new_user is True``
    :param plain_wifi_password: The password for wifi.  Only necessary if ``wifi is True``
    :param generation_purpose: Optional
    """

    pdf_data = generate_user_sheet(
        new_user,
        wifi,
        user,
        plain_user_password=plain_user_password,
        generation_purpose=generation_purpose,
        plain_wifi_password=plain_wifi_password,
    )

    pdf_storage = WebStorage(data=pdf_data, expiry=session.utcnow() + timedelta(minutes=timeout))
    session.session.add(pdf_storage)

    return pdf_storage


def get_user_sheet(sheet_id: int) -> bytes | None:
    """Fetch the storage object given an id.

    If not existent, return None.
    """
    WebStorage.auto_expire()

    if sheet_id is None:
        return None
    if (storage := session.session.get(WebStorage, sheet_id)) is None:
        return None

    return storage.data


def generate_user_sheet(
    new_user: bool,
    wifi: bool,
    user: User,
    plain_user_password: str | None = None,
    generation_purpose: str = "",
    plain_wifi_password: str = "",
) -> bytes:
    """Create a new datasheet for the given user.
    This usersheet can hold information about a user or about the wifi credentials of a user.

    This is a wrapper for
    :py:func:`pycroft.helpers.printing.generate_user_sheet` equipping
    it with the correct user id.

    This function cannot be exported to a `wrappers` module because it
    depends on `encode_type2_user_id` and is required by
    `(store|get)_user_sheet`, both in this module.

    :param new_user: Generate a page for a new created user
    :param wifi: Generate a page with the wifi credantials

    Necessary in every case:
    :param user: A pycroft user

    Only necessary if new_user=True:
    :param plain_user_password: The password

    Only necessary if wifi=True:
    :param generation_purpose: Optional purpose why this usersheet was printed
    """
    from pycroft.helpers import printing

    return generate_pdf(
        new_user=new_user,
        wifi=wifi,
        bank_account=config.membership_fee_bank_account,
        user=t.cast(printing.User, user),
        user_id=encode_type2_user_id(user.id),
        plain_user_password=plain_user_password,
        generation_purpose=generation_purpose,
        plain_wifi_password=plain_wifi_password,
    )
