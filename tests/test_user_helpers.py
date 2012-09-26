# -*- coding: utf-8 -*-

from tests import FixtureDataTestBase, make_fixture
from pycroft.lib import user as UserHelper
from tests.fixtures.user_fixtures import DormitoryData, RoomData, UserData, NetDeviceData, HostData
from pycroft.model import user, dormitory, session

class Test_010_User_Move(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, NetDeviceData, HostData]

    def setUp(self):
        super(Test_010_User_Move, self).setUp()
        self.user = user.User.q.get(1)
        self.newRoom = dormitory.Room.q.get(1)

    def test_010_moves_into_same_room(self):
        self.assertRaises(AssertionError, UserHelper.move,
            self.user, self.newRoom.dormitory, self.newRoom.level,
             self.newRoom.number, self.user)