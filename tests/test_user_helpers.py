# -*- coding: utf-8 -*-

__author__ = 'florian'

from tests import FixtureDataTestBase
from pycroft.lib import user as UserHelper, user_config
from tests.fixtures.user_fixtures import DormitoryData, FinanceAccountData, \
    RoomData, UserData, UserNetDeviceData, UserHostData, IpData, VLanData, SubnetData, \
    PatchPortData, SemesterData, TrafficGroupData, PropertyGroupData, \
    PropertyData
from pycroft.model import user, dormitory, ports, session, logging, finance, \
    properties
from datetime import datetime

class Test_010_User_Move(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, UserNetDeviceData, UserHostData,
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
        #TODO don't delete all log entries but the user log entries
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
        self.assertEqual(self.user.user_host.room, self.new_room_other_dormitory)
        #TODO test for changing ip


class Test_020_User_Move_In(FixtureDataTestBase):
    datasets = [DormitoryData, FinanceAccountData, RoomData, UserData,
                UserNetDeviceData, UserHostData, IpData, VLanData, SubnetData,
                PatchPortData, SemesterData, TrafficGroupData,
                PropertyGroupData, PropertyData]

    def setUp(self):
        super(Test_020_User_Move_In, self).setUp()
        self.processing_user = user.User.q.get(1)


    def tearDown(self):
        #TODO don't delete all log entries but the user log entries
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_020_User_Move_In, self).tearDown()

    def test_010_move_in(self):
        def get_initial_groups():
            initial_groups = []
            for group in user_config.initial_groups:
                initial_groups.append(properties.Group.q.filter(
                    properties.Group.name == group["group_name"]
                ).one())
            return initial_groups

        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_dormitory = dormitory.Dormitory.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.moves_in(test_name,
            test_login, test_email, test_dormitory,
            1,
            "1",
            None,
            test_mac,
            finance.Semester.q.first(),
            self.processing_user)

        self.assertEqual(new_user.name, test_name)
        self.assertEqual(new_user.login, test_login)
        self.assertEqual(new_user.email, test_email)
        self.assertEqual(new_user.room.dormitory, test_dormitory)
        self.assertEqual(new_user.room.number, "1")
        self.assertEqual(new_user.room.level, 1)
        self.assertEqual(new_user.user_host.user_net_device.mac, test_mac)

        #checks the initial group memberhsips
        user_groups = new_user.active_property_groups + new_user.active_traffic_groups
        for group in get_initial_groups():
            self.assertIn(group, user_groups)

        self.assertEqual(UserHelper.has_internet(new_user), True)
        user_account = finance.FinanceAccount.q.filter(
                finance.FinanceAccount.user==new_user
            ).filter(
                finance.FinanceAccount.name==u"Nutzerid: %d" % new_user.id
            ).one()
        splits = finance.Split.q.filter(
                finance.Split.account_id == user_account.id
            ).all()
        account_sum = sum([split.amount for split in splits])
        self.assertEqual(account_sum,4000)

class Test_030_User_Move_Out(FixtureDataTestBase):
    datasets = [DormitoryData, FinanceAccountData, RoomData, UserData,
                UserNetDeviceData, UserHostData, IpData, VLanData, SubnetData,
                PatchPortData, SemesterData, TrafficGroupData,
                PropertyGroupData, PropertyData]

    def setUp(self):
        super(Test_030_User_Move_Out, self).setUp()
        self.processing_user = user.User.q.get(1)

    def tearDown(self):
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_030_User_Move_Out, self).tearDown()


    def test_030_move_out(self):
        def get_initial_groups():
            initial_groups = []
            for group in user_config.initial_groups:
                initial_groups.append(properties.Group.q.filter(
                    properties.Group.name == group["group_name"]
                ).one())
            return initial_groups

        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_dormitory = dormitory.Dormitory.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.moves_in(test_name,
            test_login, test_email, test_dormitory,
            1,
            "1",
            None,
            test_mac,
            finance.Semester.q.first(),
            self.processing_user)

        out_time = datetime.now()

        UserHelper.move_out(new_user, out_time, self.processing_user)

        # check end_date of moved out user
        for membership in new_user.memberships:
            if membership.end_date >= out_time:
                self.assertEquals(membership.end_date, out_time)