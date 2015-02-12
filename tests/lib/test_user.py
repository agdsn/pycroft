# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from tests import FixtureDataTestBase
from pycroft import config
from pycroft.helpers.interval import closedopen
from pycroft.lib import user as UserHelper
from pycroft.model import (
    user, dormitory, port, session, logging, finance,  property, dns, host)
from tests.fixtures.config import ConfigData, PropertyData
from tests.fixtures.dummy.dormitory import VLANData, DormitoryData, RoomData
from tests.fixtures.dummy.finance import SemesterData, FinanceAccountData
from tests.fixtures.dummy.host import (
    IpData, SubnetData, PatchPortData,UserNetDeviceData, UserHostData)
from tests.fixtures.dummy.property import TrafficGroupData
from tests.fixtures.dummy.user import UserData


class Test_010_User_Move(FixtureDataTestBase):
    datasets = [ConfigData, DormitoryData, IpData, PatchPortData, RoomData,
                SubnetData, UserData, UserNetDeviceData, UserHostData, VLANData]

    def setUp(self):
        super(Test_010_User_Move, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.dummy.login).one()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()
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
    datasets = [ConfigData, DormitoryData, FinanceAccountData, IpData,
                PatchPortData, PropertyData, RoomData, SemesterData, SubnetData,
                TrafficGroupData, UserData, UserHostData, UserNetDeviceData,
                VLANData]

    def setUp(self):
        super(Test_020_User_Move_In, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.dummy.login).one()


    def tearDown(self):
        #TODO don't delete all log entries but the user log entries
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_020_User_Move_In, self).tearDown()

    def test_0010_move_in(self):
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
        for group in (config.member_group, config.network_access_group):
            self.assertIn(group, active_user_groups)

        self.assertTrue(UserHelper.has_network_access(new_user))
        self.assertIsNotNone(new_user.finance_account)
        self.assertEqual(new_user.finance_account.balance, 4000)
        self.assertFalse(new_user.has_property("away"))


class Test_030_User_Move_Out(FixtureDataTestBase):
    datasets = [ConfigData, FinanceAccountData, IpData, PatchPortData,
                SemesterData, TrafficGroupData]

    def setUp(self):
        super(Test_030_User_Move_Out, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

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

        UserHelper.move_out(user=new_user, comment="",
                            processor=self.processing_user, when=out_time)

        # check ends_at of moved out user
        for membership in new_user.memberships:
            self.assertIsNotNone(membership.ends_at)
            self.assertLessEqual(membership.ends_at, out_time)

        # check if users finance account still exists
        finance_account = new_user.finance_account
        self.assertIsNotNone(finance_account)


class Test_040_User_Edit_Name(FixtureDataTestBase):
    datasets = [ConfigData, DormitoryData, RoomData, UserData]

    def setUp(self):
        super(Test_040_User_Edit_Name, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

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
    datasets = [ConfigData, DormitoryData, RoomData, UserData]

    def setUp(self):
        super(Test_050_User_Edit_Email, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

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


class Test_070_User_Move_Out_Temporarily(FixtureDataTestBase):
    datasets = [ConfigData, FinanceAccountData, IpData, PatchPortData,
                PropertyData, SemesterData, TrafficGroupData]

    def setUp(self):
        super(Test_070_User_Move_Out_Temporarily, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.dummy.login).one()

    def tearDown(self):
        logging.LogEntry.q.delete()
        finance.Transaction.q.delete()
        session.session.commit()
        super(Test_070_User_Move_Out_Temporarily, self).tearDown()

    def test_0010_move_out_temporarily(self):
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

        during = closedopen(session.utcnow(), None)
        self.assertFalse(new_user.has_property("away"))

        UserHelper.move_out_temporarily(new_user, "", self.processing_user,
                                        during)
        session.session.commit()

        # check for tmpAusgezogen group membership
        self.assertIn(new_user, config.away_group.active_users())
        self.assertIn(config.away_group, new_user.active_property_groups())
        self.assertTrue(new_user.has_property("away"))

        # check if user has no ips left
        self.assertEqual(new_user.user_hosts[0].user_net_device.ips, [])

        # check log message
        log_entry = new_user.user_log_entries[-1]
        self.assertAlmostEqual(log_entry.created_at, during.begin,
                               delta=timedelta(seconds=1))
        self.assertEqual(log_entry.author, self.processing_user)


class Test_080_User_Block(FixtureDataTestBase):
    datasets = [ConfigData, DormitoryData, PropertyData, RoomData, UserData]

    def tearDown(self):
        logging.LogEntry.q.delete()
        property.Membership.q.delete()
        session.session.commit()
        super(Test_080_User_Block, self).tearDown()

    def test_0010_user_has_no_network_access(self):
        u = user.User.q.get(1)
        verstoss = property.PropertyGroup.q.filter(
            property.PropertyGroup.name == u"Verstoß").first()
#       Ich weiß nicht, ob dieser Test noch gebraucht wird!
#       self.assertTrue(u.has_property("network_access"))
        self.assertNotIn(verstoss, u.active_property_groups())

        blocked_user = UserHelper.block(u, u"test", u)
        session.session.commit()

        self.assertFalse(blocked_user.has_property("network_access"))
        self.assertIn(verstoss, blocked_user.active_property_groups())

        self.assertEqual(blocked_user.user_log_entries[0].author, u)


class Test_090_User_Is_Back(FixtureDataTestBase):
    datasets = [ConfigData, IpData, PropertyData, UserData]

    def setUp(self):
        super(Test_090_User_Is_Back, self).setUp()
        self.processing_user = user.User.q.filter_by(login='admin').one()
        self.user = user.User.q.filter_by(login='test').one()
        UserHelper.move_out_temporarily(user=self.user, comment='',
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
        self.assertAlmostEqual(log_entry.created_at, session.utcnow(),
                               delta=timedelta(seconds=5))
        self.assertEqual(log_entry.author, self.processing_user)

        self.assertFalse(self.user.has_property("away"))
