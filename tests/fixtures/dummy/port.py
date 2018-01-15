# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from fixture import DataSet

from tests.fixtures.dummy.facilities import RoomData
from .host import SwitchPortData

class SwitchPatchPortData(DataSet):
    class dummy_port1:
        name = "??"
        switch_port = SwitchPortData.dummy_port1
        room = RoomData.dummy_room1
