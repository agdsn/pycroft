# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta
from fixture import DataSet


class PropertyGroupData(DataSet):
    class group1:
        name = "group1"

    class group2:
        name = "group2"


class TrafficGroupData(DataSet):
    class group1:
        name = "traffic group1"
        credit_limit = 1000
        credit_amount = 500
        credit_interval = timedelta(days=1)
        initial_credit_amount = 3*2**30

    class group2:
        name = "traffic group2"
        credit_limit = 2000
        credit_amount = 50
        credit_interval = timedelta(hours=3)
        initial_credit_amount = 3*2**30


class PropertyData(DataSet):
    class prop_test1:
        name = "test1"
        granted = True
        property_group = PropertyGroupData.group1

    class prop_test1_1(prop_test1):
        property_group = PropertyGroupData.group2

    class prop_test2:
        name = "test2"
        granted = True
        property_group = PropertyGroupData.group2
