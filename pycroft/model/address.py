# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from __future__ import annotations
import typing as t

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, relationship, mapped_column

from pycroft.model import ddl
from pycroft.model.base import IntegerIdModel

if t.TYPE_CHECKING:
    from .facilities import Room
    from .user import User

DEFAULT_CITY = "Dresden"
DEFAULT_COUNTRY = "Germany"


class Address(IntegerIdModel):
    """A known address.

    Addresses differ from most other entities such as users or rooms in the following ways:

    - Their identity is provided by their value, i.e. if two addresses have equal values,
      they should be identitcal
    - Their existence is justified solely by the reference of another object.
      At no point in time should there be any unreferenced address records in the db.
    - They should be immutable: This implies that editing e.g. the street of a user's address
      should not change the street of the corresponding room's address.
      This implies that addresses are *stateless*, i.e. have no life cycle.

    Establishing these consistencies requires triggers.
    """
    street: Mapped[str]
    number: Mapped[str]
    addition: Mapped[str] = mapped_column(server_default="")
    # Sometimes, zipcodes can contain things like dashes, so rather take String().
    # we could probably impose some format by a check but that would be over engineering
    zip_code: Mapped[str]
    city: Mapped[str] = mapped_column(server_default=DEFAULT_CITY)
    state: Mapped[str] = mapped_column(server_default="")
    country: Mapped[str] = mapped_column(server_default=DEFAULT_COUNTRY)

    __table_args__ = (
        UniqueConstraint('street', 'number', 'addition', 'zip_code', 'city', 'state', 'country'),
    )

    # backrefs
    rooms: Mapped[list[Room]] = relationship(back_populates="address")
    inhabitants: Mapped[list[User]] = relationship(back_populates="address")
    # /backrefs

    def __str__(self):
        return f"{self:short}"

    def __format__(self, spec="short"):
        """Return the address items separated by the format specifier"""
        city = self.city.upper() if self.country and self.country != DEFAULT_COUNTRY else self.city
        items: list[str] = [f"{self.street} {self.number} // {self.addition}" if self.addition
                            else f"{self.street} {self.number}", f"{self.zip_code} {city}"]
        if self.state:
            state = self.state.upper() if self.country and self.country != DEFAULT_COUNTRY else self.state
            items.append(f"{state}")
        if self.country and self.country != DEFAULT_COUNTRY:
            items.append(f"{self.country.upper()}")

        glue = ", " if spec == "short" else "\n" if spec == "long" else spec
        return glue.join(items)


manager = ddl.DDLManager()

address_remove_orphans = ddl.Function(
    'address_remove_orphans', [], 'trigger',
    """ BEGIN
      delete from address
      where not exists (select 1 from room where room.address_id = address.id)
      and not exists (select 1 from "user" where "user".address_id = address.id);
      RETURN NULL;
    END;""",
    volatility='volatile', strict=True,  language='plpgsql'
)
manager.add_function(Address.__table__, address_remove_orphans)
# User trigger for the respective backref added in `user.py`
# Room trigger for the respective backref added in `facilities.py`
manager.register()
