# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'florian'

from tests import FixtureDataTestBase, make_fixture
from pycroft.lib import user as UserHelper
from tests.fixtures.user_fixtures import DormitoryData, RoomData, UserData, NetDeviceData, HostData, IpData, VLanData, SubnetData, PatchPortData
from pycroft.model import user, dormitory, ports, session, logging

class Test_010_User_Move(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, NetDeviceData, HostData,
                IpData, VLanData, SubnetData, PatchPortData]

    def setUp(self):
        super(Test_010_User_Move, self).setUp()
        self.user = user.User.q.get(1)
        self.processing_user = user.User.q.get(2)
        self.old_room = dormitory.Room.q.get(1)
        self.new_room_other_dormitory = dormitory.Room.q.get(2)
        self.new_room_same_dormitory = dormitory.Room.q.get(3)
        self.new_patch_port = ports.PatchPort.q.get(2)

    def tearDown(self):
        #TODO dont delete all log entries but the userlogentries
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_010_User_Move, self).tearDown()


    def test_010_moves_into_same_room(self):
        self.assertRaises(AssertionError, UserHelper.move,
            self.user, self.old_room.dormitory, self.old_room.level,
            self.old_room.number, self.processing_user)

    def test_020_moves_into_other_dormitory(self):
        UserHelper.move(self.user, self.new_room_other_dormitory.dormitory,
            self.new_room_other_dormitory.level,
            self.new_room_other_dormitory.number, self.processing_user)
        self.assertEqual(self.user.room, self.new_room_other_dormitory)
        self.assertEqual(self.user.hosts[0].room, self.new_room_other_dormitory)

