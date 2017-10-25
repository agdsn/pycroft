# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, timedelta

from fixture import DataSet

from tests.fixtures.dummy.host import IPData
from tests.fixtures.dummy.user import UserData

class TrafficVolumeData(DataSet):
    class dummy_volume:
        ip = IPData.dummy_user_ipv4
        user = UserData.dummy
        type = "IN"
        amount = int(7.6 * 2**20)
        packets = int(7600)
        timestamp = datetime.utcnow()

    class dummy_volume_before_balance:
        ip = IPData.dummy_user_ipv4
        user = UserData.dummy
        type = "IN"
        amount = int(3.72 * 2**30)
        packets = int(3720)
        timestamp = datetime.utcnow() - timedelta(hours=2)

    class dummy_volume_ipv6:
        ip = IPData.dummy_user_ipv6
        user = UserData.dummy
        type = "OUT"
        amount = int(56.1 * 2**20)
        packets = int(5610)
        timestamp = datetime.utcnow() - timedelta(minutes=25)

    class dummy_volume_server:
        ip = IPData.dummy_server_ip
        user = UserData.dummy
        type = "IN"
        amount = int(12.22 * 2**20)
        packets = int(1222)
        timestamp = datetime.utcnow() - timedelta(minutes=25)

    class dummy_volume_switch:
        ip = IPData.dummy_switch_ip
        user = UserData.privileged
        type = "IN"
        amount = int(51.258 * 2**40)
        packets = int(51258)
        timestamp = datetime.utcnow() - timedelta(hours=6)


class TrafficCreditData(DataSet):
    class dummy_credit:
        user= UserData.dummy
        amount = int(5.47 * 2**30)
        timestamp = datetime.utcnow() - timedelta(minutes=20)

    class dummy_credit_before_balance:
        user = UserData.dummy
        amount = int(62.1 * 2**20)
        timestamp = datetime.utcnow() - timedelta(hours=3)

    class dummy_credit_in_future:
        user = UserData.dummy
        amount = int(3 * 2**30)
        timestamp = datetime.utcnow() + timedelta(days=1)


class TrafficBalanceData(DataSet):
    class dummy_balance:
        user = UserData.dummy
        timestamp = datetime.utcnow() - timedelta(hours=1)
        amount = int(2.73 * 2**20)

    class dummy_balance3:
        user = UserData.anotheruser
        timestamp = datetime.utcnow() + timedelta(days=1)
        amount = int(6.12 * 2**30)

