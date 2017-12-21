# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, timedelta

from fixture import DataSet

from tests.fixtures.dummy.user import UserData


class PropertyGroupData(DataSet):
    class dummy:
        name = "dummy_property_group"


class MembershipData(DataSet):
    class dummy_membership:
        begins_at = datetime.utcnow() - timedelta(1)
        ends_at = datetime.utcnow() + timedelta(1)
        group = PropertyGroupData.dummy
        user = UserData.dummy


class PropertyData(DataSet):
    class granted:
        property_group = PropertyGroupData.dummy
        name = "granted_property"
        granted = True

    class denied:
        property_group = PropertyGroupData.dummy
        name = "denied_property"
        granted = False


class TrafficGroupData(DataSet):
    class dummy:
        name = "dummy"
        credit_limit = 7*2**30
        credit_amount = 2*2**30
        credit_interval = timedelta(days=1)
        initial_credit_amount = 3*2**30
