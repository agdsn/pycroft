# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime

from fixture import DataSet

from tests.fixtures.dummy.host import IPData
from tests.fixtures.dummy.user import UserData


class TrafficVolumeData(DataSet):
    class dummy_volume:
        size = 1000
        timestamp = datetime.utcnow()
        traffic_type = "IN"
        ip = IPData.dummy_user_ipv4


class TrafficCreditData(DataSet):
    class traffic_credit1:
        id = 1
        user = UserData.traffic_user1
        grant_date = datetime.utcnow()
        amount = 1000
        added_amount = 100
