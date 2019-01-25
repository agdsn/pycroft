# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet


class PropertyGroupData(DataSet):
    class group1:
        name = "group1"

    class group2:
        name = "group2"


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
