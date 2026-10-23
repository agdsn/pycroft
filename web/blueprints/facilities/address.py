import typing as t

from sqlalchemy.orm import Session, Query
from sqlalchemy.orm.attributes import InstrumentedAttribute

from pycroft.model.address import Address

ADDRESS_ENTITIES = {
    "street": Address.street,
    "number": Address.number,
    "addition": Address.addition,
    "zip_code": Address.zip_code,
    "city": Address.city,
    "state": Address.state,
    "country": Address.country,
}


def get_address_entity(type: str) -> InstrumentedAttribute[str]:
    try:
        return ADDRESS_ENTITIES[type]
    except KeyError:
        raise ValueError(
            f"Unknown Address type '{type!r}'. Accepted: {' '.join(ADDRESS_ENTITIES)}"
        ) from None


def address_entity_search_query(
    query: str, entity: InstrumentedAttribute[str], session: Session, limit: int
) -> Query[t.Any]:
    return (
        session.query()
        .add_columns(entity)
        .distinct()
        .filter(entity.ilike(f"%{query}%"))
        .order_by(entity.asc())
        .limit(limit)
    )
