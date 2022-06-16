import typing

from pycroft.model.address import Address
from pycroft.model.session import session, with_transaction


@with_transaction
def get_or_create_address(
    street: str,
    number: str,
    addition: str | None,
    zip_code: str,
    city: str | None = None,
    state: str | None = None,
    country: str | None = None,
) -> Address:
    """Returns an existing address or creates a new one.

    If the address is to be used for some other update operation,
    make sure to wrap this call and the next one in a `Session.no_autoflush` block,
    because else the address cleanup trigger may fire.
    """
    query = session.query(Address).filter_by(
        street=street,
        number=number,
        addition=addition,
        zip_code=zip_code,
        city=city,
        state=state,
        country=country,
    )
    num_matching = query.count()
    if num_matching == 1:
        return typing.cast(Address, query.one())

    if num_matching > 1:
        raise RuntimeError("Found more than one address")

    # create
    new_address = Address(
        street=street,
        number=number,
        addition=addition,
        zip_code=zip_code,
        city=city,
        state=state,
        country=country,
    )
    session.add(new_address)
    return new_address
