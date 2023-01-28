# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.config
~~~~~~~~~~~~~~~~~~~~
"""
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship, Mapped

from pycroft.model.base import IntegerIdModel
from pycroft.model.finance import Account, BankAccount
from pycroft.model.user import PropertyGroup


class Config(IntegerIdModel):
    member_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False
    )
    member_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[member_group_id]
    )
    network_access_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    network_access_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[network_access_group_id])
    violation_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    violation_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[violation_group_id])
    external_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    external_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[external_group_id])
    blocked_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    blocked_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[blocked_group_id])
    caretaker_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    caretaker_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[caretaker_group_id])
    treasurer_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    treasurer_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[treasurer_group_id])
    pre_member_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    pre_member_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[pre_member_group_id]
    )
    traffic_limit_exceeded_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False
    )
    traffic_limit_exceeded_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[traffic_limit_exceeded_group_id]
    )
    payment_in_default_group_id: Mapped[int] = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False
    )
    payment_in_default_group: Mapped[PropertyGroup] = relationship(
        PropertyGroup, foreign_keys=[payment_in_default_group_id]
    )
    membership_fee_account_id: Mapped[int] = Column(
        Integer, ForeignKey(Account.id), nullable=False)
    membership_fee_account: Mapped[Account] = relationship(
        Account, foreign_keys=[membership_fee_account_id])
    membership_fee_bank_account_id: Mapped[Mapped[int]] = Column(
        Integer, ForeignKey(BankAccount.id), nullable=False)
    membership_fee_bank_account: Mapped[BankAccount] = relationship(
        BankAccount, foreign_keys=[membership_fee_bank_account_id])
    fints_product_id: Mapped[str] = Column(String, nullable=True)

    __table_args__ = (CheckConstraint("id = 1"),)
