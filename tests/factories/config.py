# -*- coding: utf-8 -*-
# Copyright (c) 2018 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from factory import SubFactory

from pycroft.model.config import Config
from .base import BaseFactory
from .finance import AccountFactory
from .property import PropertyGroupFactory


class ConfigFactory(BaseFactory):
    """This is a dummy Config factory, Referencing PropertyGroups with
    no a-priori property relationships and arbitrary Accounts.
    """
    class Meta:
        model = Config

    id = 1

    # `PropertyGroup`s
    member_group = SubFactory(PropertyGroupFactory)
    network_access_group = SubFactory(PropertyGroupFactory)
    violation_group = SubFactory(PropertyGroupFactory)
    moved_from_division_group = SubFactory(PropertyGroupFactory)
    already_paid_semester_fee_group = SubFactory(PropertyGroupFactory)
    cache_group = SubFactory(PropertyGroupFactory)

    # `Account`s
    registration_fee_account = SubFactory(AccountFactory)
    semester_fee_account = SubFactory(AccountFactory)
    late_fee_account = SubFactory(AccountFactory)
    additional_fee_account = SubFactory(AccountFactory)
