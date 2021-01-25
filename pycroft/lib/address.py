from typing import overload, Optional

from pycroft.model.address import Address
from pycroft.model.session import session, with_transaction


@overload
def get_or_create_address(
    street: str,
    number: str,
    addition: Optional[str],
    zip_code: str,
    city: Optional[str],
    state: Optional[str],
    country: Optional[str],
) -> Address: ...


@with_transaction
def get_or_create_address(**kwargs) -> Address:
    query = session.query(Address).filter_by(**kwargs)
    num_matching = query.count()
    if num_matching == 1:
        return query.one()

    if num_matching > 1:
        raise RuntimeError("Found more than one address")

    # create
    new_address = Address(**kwargs)
    session.add(new_address)
    return new_address
