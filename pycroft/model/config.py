# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.config
~~~~~~~~~~~~~~~~~~~~
"""
import typing as t
from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column as col

from pycroft.model.base import IntegerIdModel
from pycroft.model.finance import Account, BankAccount
from pycroft.model.user import PropertyGroup


fkey_pgroup = t.Annotated[int, col(ForeignKey(PropertyGroup.id))]
class Config(IntegerIdModel):
    member_group_id: Mapped[fkey_pgroup] = col()
    member_group: Mapped[PropertyGroup] = relationship(foreign_keys=[member_group_id])

    network_access_group_id: Mapped[fkey_pgroup] = col()
    network_access_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[network_access_group_id]
    )

    violation_group_id: Mapped[fkey_pgroup] = col()
    violation_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[violation_group_id]
    )

    external_group_id: Mapped[fkey_pgroup] = col()
    external_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[external_group_id]
    )

    blocked_group_id: Mapped[fkey_pgroup] = col()
    blocked_group: Mapped[PropertyGroup] = relationship(foreign_keys=[blocked_group_id])

    caretaker_group_id: Mapped[fkey_pgroup] = col()
    caretaker_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[caretaker_group_id]
    )

    treasurer_group_id: Mapped[fkey_pgroup] = col()
    treasurer_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[treasurer_group_id]
    )

    pre_member_group_id: Mapped[fkey_pgroup] = col()
    pre_member_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[pre_member_group_id]
    )

    traffic_limit_exceeded_group_id: Mapped[fkey_pgroup] = col()
    traffic_limit_exceeded_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[traffic_limit_exceeded_group_id]
    )

    payment_in_default_group_id: Mapped[fkey_pgroup] = col()
    payment_in_default_group: Mapped[PropertyGroup] = relationship(
        foreign_keys=[payment_in_default_group_id]
    )

    membership_fee_account_id: Mapped[int] = col(ForeignKey(Account.id))
    membership_fee_account: Mapped[Account] = relationship(
        foreign_keys=[membership_fee_account_id]
    )

    membership_fee_bank_account_id: Mapped[int] = col(ForeignKey(BankAccount.id))
    membership_fee_bank_account: Mapped[BankAccount] = relationship(
        foreign_keys=[membership_fee_bank_account_id]
    )

    fints_product_id: Mapped[str | None]

    __table_args__ = (CheckConstraint("id = 1"),)
