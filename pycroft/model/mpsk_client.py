#  Copyright (c) 2024. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details

from __future__ import annotations

from packaging.utils import InvalidName
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, validates, Mapped, mapped_column
from sqlalchemy.types import String

from pycroft.helpers.net import mac_regex
from pycroft.model.base import IntegerIdModel
from pycroft.model.host import MulticastFlagException
from pycroft.model.type_aliases import mac_address
from pycroft.model.types import InvalidMACAddressException
from pycroft.model.user import User


class MPSKClient(IntegerIdModel):

    name: Mapped[str] = mapped_column(String, nullable=False)

    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey(User.id, ondelete="CASCADE"), index=True, nullable=False
    )
    owner: Mapped[User] = relationship(User, back_populates="mpsk_clients")
    mac: Mapped[mac_address] = mapped_column(unique=True)

    @validates("mac")
    def validate_mac(self, _, mac_address):
        match = mac_regex.match(mac_address)
        if not match:
            raise InvalidMACAddressException(f"MAC address {mac_address!r} is not valid")
        if int(mac_address[0:2], base=16) & 1:
            raise MulticastFlagException("Multicast bit set in MAC address")
        return mac_address

    @validates("name")
    def validate_name(self, _, name):
        if name.strip() == "":
            raise InvalidName("Name cannot be empty")

        return name
