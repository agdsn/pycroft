# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from pycroft.model.address import Address
from pycroft.model.base import IntegerIdModel
from pycroft.model.finance import Account, BankAccount
from pycroft.model.user import PropertyGroup


class Config(IntegerIdModel):
    member_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    member_group = relationship(PropertyGroup, foreign_keys=[member_group_id])
    network_access_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    network_access_group = relationship(
        PropertyGroup, foreign_keys=[network_access_group_id])
    violation_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    violation_group = relationship(
        PropertyGroup, foreign_keys=[violation_group_id])
    external_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    external_group = relationship(
        PropertyGroup, foreign_keys=[external_group_id])
    blocked_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    blocked_group = relationship(
        PropertyGroup, foreign_keys=[blocked_group_id])
    caretaker_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    caretaker_group = relationship(
        PropertyGroup, foreign_keys=[caretaker_group_id])
    treasurer_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    treasurer_group = relationship(
        PropertyGroup, foreign_keys=[treasurer_group_id])
    cache_group_id = Column(Integer, ForeignKey(PropertyGroup.id),
                            nullable=False)
    cache_group = relationship(PropertyGroup, foreign_keys=[cache_group_id])
    traffic_limit_exceeded_group_id = Column(Integer, ForeignKey(PropertyGroup.id),
                            nullable=False)
    traffic_limit_exceeded_group = relationship(PropertyGroup,
                                                foreign_keys=[traffic_limit_exceeded_group_id])
    payment_in_default_group_id = Column(Integer, ForeignKey(PropertyGroup.id),
                            nullable=False)
    payment_in_default_group = relationship(PropertyGroup, foreign_keys=[payment_in_default_group_id])
    membership_fee_account_id = Column(
        Integer, ForeignKey(Account.id), nullable=False)
    membership_fee_account = relationship(
        Account, foreign_keys=[membership_fee_account_id])
    membership_fee_bank_account_id = Column(
        Integer, ForeignKey(BankAccount.id), nullable=False)
    membership_fee_bank_account = relationship(
        BankAccount, foreign_keys=[membership_fee_bank_account_id])

    __table_args__ = (CheckConstraint("id = 1"),)
