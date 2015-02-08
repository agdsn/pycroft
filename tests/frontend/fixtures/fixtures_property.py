#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

import datetime
from fixture import DataSet

from fixtures_user import UserData


class BaseMembership():
    """Base class with data every membership model needs"""
    begins_at = datetime.datetime.utcnow()
    ends_at = None


class BaseProperty():
    """Base class with data every property model needs"""
    granted = True


class PropertyGroupData(DataSet):
    class property_group1_admin:
        name = "Admin"

    class property_group2_finance:
        name = "Finanzer"


class PropertyData(DataSet):
    class property1_dormitories_show(BaseProperty):
        name = "dormitories_show"
        property_group = PropertyGroupData.property_group1_admin

    class property2_dormitories_change(BaseProperty):
        name = "dormitories_change"
        property_group = PropertyGroupData.property_group1_admin

    class property3_finance_show(BaseProperty):
        name = "finance_show"
        property_group = PropertyGroupData.property_group2_finance

    class property4_finance_change(BaseProperty):
        name = "finance_change"
        property_group = PropertyGroupData.property_group2_finance


class MembershipData(DataSet):
    class membership1_user1_admin(BaseMembership):
        group = PropertyGroupData.property_group1_admin
        user = UserData.user1_admin

    class membership2_user2_admin(BaseMembership):
        group = PropertyGroupData.property_group1_admin
        user = UserData.user2_finance

    class membership3_user2_finance(BaseMembership):
        group = PropertyGroupData.property_group2_finance
        user = UserData.user2_finance
