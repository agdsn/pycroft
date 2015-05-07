# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer
from sqlalchemy.orm import relationship
from pycroft.model.base import ModelBase
from pycroft.model.dns import DNSZone
from pycroft.model.finance import FinanceAccount
from pycroft.model.user import PropertyGroup


class Config(ModelBase):
    member_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    member_group = relationship(PropertyGroup, foreign_keys=[member_group_id])
    network_access_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    network_access_group = relationship(
        PropertyGroup, foreign_keys=[network_access_group_id])
    away_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    away_group = relationship(PropertyGroup, foreign_keys=[away_group_id])
    violation_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    violation_group = relationship(
        PropertyGroup, foreign_keys=[violation_group_id])
    moved_from_division_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    moved_from_division_group = relationship(
        PropertyGroup, foreign_keys=[moved_from_division_group_id])
    already_paid_semester_fee_group_id = Column(
        Integer, ForeignKey(PropertyGroup.id), nullable=False)
    already_paid_semester_fee_group = relationship(
        PropertyGroup, foreign_keys=[already_paid_semester_fee_group_id])
    registration_fee_account_id = Column(
        Integer, ForeignKey(FinanceAccount.id), nullable=False)
    registration_fee_account = relationship(
        FinanceAccount, foreign_keys=[registration_fee_account_id])
    semester_fee_account_id = Column(
        Integer, ForeignKey(FinanceAccount.id), nullable=False)
    semester_fee_account = relationship(
        FinanceAccount, foreign_keys=[semester_fee_account_id])
    late_fee_account_id = Column(
        Integer, ForeignKey(FinanceAccount.id), nullable=False)
    late_fee_account = relationship(
        FinanceAccount, foreign_keys=[late_fee_account_id])
    additional_fee_account_id = Column(
        Integer, ForeignKey(FinanceAccount.id), nullable=False)
    additional_fee_account = relationship(
        FinanceAccount, foreign_keys=[additional_fee_account_id])
    user_zone_id = Column(Integer, ForeignKey(DNSZone.id), nullable=False)
    user_zone = relationship(DNSZone)
    __table_args__ = (CheckConstraint("id = 1"),)
