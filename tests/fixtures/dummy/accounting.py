# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime

from fixture import DataSet

from tests.fixtures.dummy.host import IpData


class TrafficVolumeData(DataSet):
    class dummy_volume:
        size = 1000
        timestamp = datetime.utcnow()
        type = "IN"
        ip = IpData.dummy_user_ipv4
