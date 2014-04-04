#!/usr/bin/env python
# -*- coding: utf-8 -*-

from fixture import DataSet


class DormitoryData(DataSet):
    class dummy_house1:
        id = 1
        number = "01"
        short_name = "abc"
        street = "dummy"


class BaseRoom():
    """Base class with data every room model needs"""
    inhabitable = True
    dormitory = DormitoryData.dummy_house1


class RoomData(DataSet):
    class dummy_room1(BaseRoom):
        id = 1
        number = 1
        level = 1

    class dummy_room2(BaseRoom):
        id = 2
        number = 2
        level = 1

