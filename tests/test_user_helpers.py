# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from tests import FixtureDataTestBase, make_fixture
from pycroft.lib import user as UserHelper
from tests.fixtures.user_fixtures import DormitoryData, RoomData, UserData, NetDeviceData, HostData
from pycroft.model import user, dormitory, session

class Test_010_User_Move(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, NetDeviceData, HostData]

    def setUp(self):
        super(Test_010_User_Move, self).setUp()
        self.user = user.User.q.get(1)
        self.old_room = dormitory.Room.q.get(1)
        self.new_room_other_dormitory = dormitory.Room.q.get(2)
        self.new_room_same_dormitory = dormitory.Room.q.get(3)

    def test_010_moves_into_same_room(self):
        self.assertRaises(AssertionError, UserHelper.move,
            self.user, self.old_room.dormitory, self.old_room.level,
             self.old_room.number, self.user)
