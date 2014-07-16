# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from tests import FixtureDataTestBase
from pycroft import config
from pycroft.helpers.interval import Interval
from pycroft.lib import user as UserHelper
from tests.lib.fixtures.user_fixtures import DormitoryData, FinanceAccountData, \
    RoomData, UserData, UserNetDeviceData, UserHostData, IpData, VLANData, SubnetData, \
    PatchPortData, SemesterData, TrafficGroupData, PropertyGroupData, \
    PropertyData, MembershipData
from pycroft.model import user, dormitory, port, session, logging, finance, \
    property, dns, host


class Test_010_User_Move(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, UserNetDeviceData, UserHostData,
                IpData, VLANData, SubnetData, PatchPortData]

    def setUp(self):
        super(Test_010_User_Move, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.dummy_user1.login).one()
        self.processing_user = user.User.q.filter_by(
            login=UserData.dummy_user2.login).one()
        self.old_room = self.user.room #dormitory.Room.q.get(1)
        self.same_dormitory = dormitory.Dormitory.q.filter_by(
            short_name=DormitoryData.dummy_house1.short_name).one()
        assert self.same_dormitory == self.old_room.dormitory
        self.other_dormitory = dormitory.Dormitory.q.filter_by(
            short_name=DormitoryData.dummy_house2.short_name).one()

        self.new_room_other_dormitory = dormitory.Room.q.filter_by(
            dormitory=self.other_dormitory).one()
        self.new_room_same_dormitory = dormitory.Room.q.filter_by(
            dormitory=self.same_dormitory, number=RoomData.dummy_room3.number,
            level=RoomData.dummy_room3.level, inhabitable=True).one()
        self.new_patch_port = port.PatchPort.q.filter_by(
            name=PatchPortData.dummy_patch_port2.name).one()

    def tearDown(self):
        #TODO don't delete all log entries but the user log entries
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_010_User_Move, self).tearDown()

    def test_0010_moves_into_same_room(self):
        self.assertRaisesInTransaction(
            AssertionError, UserHelper.move, self.user, self.old_room.dormitory,
            self.old_room.level, self.old_room.number, self.processing_user)

    def test_0020_moves_into_other_dormitory(self):
        UserHelper.move(self.user, self.new_room_other_dormitory.dormitory,
            self.new_room_other_dormitory.level,
            self.new_room_other_dormitory.number, self.processing_user)
        self.assertEqual(self.user.room, self.new_room_other_dormitory)
        self.assertEqual(self.user.user_hosts[0].room, self.new_room_other_dormitory)
        #TODO test for changing ip


class Test_020_User_Move_In(FixtureDataTestBase):
    datasets = [DormitoryData, FinanceAccountData, RoomData, UserData,
                UserNetDeviceData, UserHostData, IpData, VLANData, SubnetData,
                PatchPortData, SemesterData, TrafficGroupData,
                PropertyGroupData, PropertyData]

    def setUp(self):
        super(Test_020_User_Move_In, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.dummy_user1.login).one()


    def tearDown(self):
        #TODO don't delete all log entries but the user log entries
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_020_User_Move_In, self).tearDown()

    def test_0010_move_in(self):
        def get_initial_groups():
            initial_groups = []
            for memberships in config["move_in"]["default_group_memberships"]:
                initial_groups.append(property.Group.q.filter(
                    property.Group.name == memberships["name"]
                ).one())
            return initial_groups

        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_dormitory = dormitory.Dormitory.q.first()
        test_hostname = "hans"
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_dormitory,
            level=1,
            room_number="1",
            host_name=test_hostname,
            mac=test_mac,
            processor=self.processing_user,
            moved_from_division=False,
            already_paid_semester_fee=False
        )

        self.assertEqual(new_user.name, test_name)
        self.assertEqual(new_user.login, test_login)
        self.assertEqual(new_user.email, test_email)
        self.assertEqual(new_user.room.dormitory, test_dormitory)
        self.assertEqual(new_user.room.number, "1")
        self.assertEqual(new_user.room.level, 1)
        self.assertEqual(new_user.user_hosts[0].user_net_device.mac, test_mac)

        user_host = host.UserHost.q.filter_by(user=new_user).one()
        user_net_device = host.UserNetDevice.q.filter_by(host=user_host).one()
        self.assertEqual(user_net_device.mac, test_mac)
        user_cname_record = dns.CNAMERecord.q.filter_by(host=user_host).one()
        self.assertEqual(user_cname_record.name, test_hostname)
        user_a_record = dns.ARecord.q.filter_by(host=user_host).one()
        self.assertEqual(user_cname_record.record_for, user_a_record)

        # checks the initial group memberships
        active_user_groups = (new_user.active_property_groups() +
                              new_user.active_traffic_groups())
        for group in get_initial_groups():
            self.assertIn(group, active_user_groups)

        self.assertEqual(UserHelper.has_internet(new_user), True)
        self.assertIsNotNone(new_user.finance_account)
        self.assertEqual(new_user.finance_account.balance, 4000)
        self.assertFalse(new_user.has_property("away"))


class Test_030_User_Move_Out(FixtureDataTestBase):
    datasets = [IpData, PatchPortData, SemesterData, TrafficGroupData,
                PropertyGroupData, FinanceAccountData]

    def setUp(self):
        super(Test_030_User_Move_Out, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.dummy_user2.login).one()

    def tearDown(self):
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_030_User_Move_Out, self).tearDown()

    def test_0030_move_out(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_dormitory = dormitory.Dormitory.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_dormitory,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            moved_from_division=False,
            already_paid_semester_fee=False
        )
        session.session.commit()

        out_time = session.utcnow()

        UserHelper.move_out(user=new_user, date=out_time, comment="",
            processor=self.processing_user)

        # check end_date of moved out user
        for membership in new_user.memberships:
            self.assertIsNotNone(membership.end_date)
            self.assertLessEqual(membership.end_date, out_time)

        # check if users finance account still exists
        finance_account = new_user.finance_account
        self.assertIsNotNone(finance_account)


class Test_040_User_Edit_Name(FixtureDataTestBase):
    datasets = [RoomData, DormitoryData, UserData]

    def setUp(self):
        super(Test_040_User_Edit_Name, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.dummy_user2.login).one()

    def tearDown(self):
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_040_User_Edit_Name, self).tearDown()

    def test_0010_correct_new_name(self):
        print self.user.name
        print self.user.id

        UserHelper.edit_name(self.user, "toller neuer Name", self.user)

        self.assertEqual(self.user.name, "toller neuer Name")

    def test_0020_name_zero_length(self):
        old_name = self.user.name

        UserHelper.edit_name(self.user, "", self.user)

        self.assertEqual(self.user.name, old_name)


class Test_050_User_Edit_Email(FixtureDataTestBase):
    datasets = [RoomData, DormitoryData, UserData]

    def setUp(self):
        super(Test_050_User_Edit_Email, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.dummy_user2.login).one()

    def tearDown(self):
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_050_User_Edit_Email, self).tearDown()

    def test_0010_correct_new_email(self):
        UserHelper.edit_email(self.user, "sebastian@schrader.de", self.user)

        self.assertEqual(self.user.email, "sebastian@schrader.de")

    def test_0020_email_zero_length(self):
        old_email = self.user.email

        UserHelper.edit_email(self.user, "", self.user)

        self.assertEqual(self.user.email, old_email)


class Test_070_User_Move_Out_Tmp(FixtureDataTestBase):
    datasets = [IpData, PatchPortData, SemesterData, TrafficGroupData,
                PropertyGroupData, PropertyData, FinanceAccountData]

    def setUp(self):
        super(Test_070_User_Move_Out_Tmp, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.dummy_user1.login).one()

    def tearDown(self):
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_070_User_Move_Out_Tmp, self).tearDown()

    def test_0010_move_out_tmp(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_dormitory = dormitory.Dormitory.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_dormitory,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            moved_from_division=False,
            already_paid_semester_fee=False
        )
        session.session.commit()

        out_time = session.utcnow()
        self.assertFalse(new_user.has_property("away"))

        UserHelper.move_out_tmp(new_user, out_time, "", self.processing_user)
        session.session.commit()

        # check for tmpAusgezogen group membership
        away_group = property.PropertyGroup.q.filter(
            property.PropertyGroup.name == config["move_out_tmp"]["group"]).one()
        self.assertIn(new_user, away_group.active_users())
        self.assertIn(away_group, new_user.active_property_groups())
        self.assertTrue(new_user.has_property("away"))

        # check if user has no ips left
        self.assertEqual(new_user.user_hosts[0].user_net_device.ips, [])

        # check log message
        log_entry = new_user.user_log_entries[-1]
        self.assertGreaterEqual(log_entry.timestamp, out_time)
        self.assertEqual(log_entry.author, self.processing_user)


class Test_080_User_Block(FixtureDataTestBase):
    datasets = [DormitoryData, RoomData, UserData, PropertyGroupData,
                PropertyData]

    def tearDown(self):
        logging.LogEntry.q.delete()
        property.Membership.q.delete()
        session.session.commit()
        super(Test_080_User_Block, self).tearDown()

    def test_0010_user_has_no_internet(self):
        u = user.User.q.get(1)
        verstoss = property.PropertyGroup.q.filter(
            property.PropertyGroup.name == u"Verstoß").first()
#       Ich weiß nicht, ob dieser Test noch gebraucht wird!
#       self.assertTrue(u.has_property("internet"))
        self.assertNotIn(verstoss, u.active_property_groups())

        blocked_user = UserHelper.block(u, u"test", u)
        session.session.commit()

        self.assertFalse(blocked_user.has_property("internet"))
        self.assertIn(verstoss, blocked_user.active_property_groups())

        self.assertEqual(blocked_user.user_log_entries[0].author, u)


class Test_090_User_Is_Back(FixtureDataTestBase):
    datasets = [IpData, PropertyData, PropertyGroupData, UserData]

    def setUp(self):
        super(Test_090_User_Is_Back, self).setUp()
        self.processing_user = user.User.q.filter_by(login='admin').one()
        self.user = user.User.q.filter_by(login='test').one()
        UserHelper.move_out_tmp(user=self.user,
                                date=session.utcnow(),
                                comment='',
                                processor=self.processing_user)
        session.session.commit()

    def tearDown(self):
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_090_User_Is_Back, self).tearDown()

    def test_0010_user_is_back(self):
        self.assertTrue(self.user.has_property("away"))
        UserHelper.is_back(self.user, self.processing_user)
        session.session.commit()

        # check whether user has at least one ip
        self.assertNotEqual(self.user.user_hosts[0].user_net_device.ips, [])

        # check log message
        log_entry = self.user.user_log_entries[-1]
        self.assertAlmostEqual(log_entry.timestamp, session.utcnow(),
                               delta=timedelta(seconds=5))
        self.assertEqual(log_entry.author, self.processing_user)

        self.assertFalse(self.user.has_property("away"))


class Test_100_User_has_property(FixtureDataTestBase):

    datasets = [PropertyData, PropertyGroupData, UserData, MembershipData]

    def setUp(self):
        super(Test_100_User_has_property, self).setUp()
        self.test_user = user.User.q.filter_by(
            login=UserData.dummy_user2.login).one()

    def test_0010_positive_test(self):
        self.assertTrue(self.test_user.has_property(PropertyData.dummy.name))
        self.assertIsNotNone(
            user.User.q.filter(
                user.User.login == self.test_user.login,
                user.User.has_property(PropertyData.dummy.name)
            ).first())

    def test_0020_negative_test(self):
        self.assertFalse(self.test_user.has_property(PropertyData.away.name))
        self.assertIsNone(
            user.User.q.filter(
                user.User.login == self.test_user.login,
                user.User.has_property(PropertyData.away.name)
            ).first())

    def test_0030_positive_test_interval(self):
        interval = Interval(MembershipData.dummy_membership1.start_date,
                            MembershipData.dummy_membership1.end_date)
        self.assertTrue(
            self.test_user.has_property(PropertyData.dummy.name, interval)
        )
        self.assertIsNotNone(
            user.User.q.filter(
                user.User.login == self.test_user.login,
                user.User.has_property(PropertyData.dummy.name, interval)
            ).first())

    def test_0030_negative_test_interval(self):
        interval = Interval(
            MembershipData.dummy_membership1.end_date + timedelta(1),
            MembershipData.dummy_membership1.end_date + timedelta(2)
        )
        self.assertFalse(
            self.test_user.has_property(PropertyData.dummy.name, interval)
        )
        self.assertIsNone(
            user.User.q.filter(
                user.User.login == self.test_user.login,
                user.User.has_property(PropertyData.dummy.name, interval)
            ).first())
