from typing import overload, Optional

from pycroft.model.address import Address
from pycroft.model.session import session, with_transaction


@with_transaction
def get_or_create_address(
    street: str,
    number: str,
    addition: Optional[str],
    zip_code: str,
    city: Optional[str],
    state: Optional[str],
    country: Optional[str],
) -> Address:
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
        return query.one()

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
