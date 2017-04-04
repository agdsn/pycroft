# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.model.port import PatchPort
from pycroft.model.user import Membership, PropertyGroup
from tests import FixtureDataTestBase
from pycroft import config
from pycroft.helpers.interval import closedopen
from pycroft.lib import user as UserHelper
from pycroft.model import (
    user, facilities, session, logging, finance, host)
from tests.fixtures.config import ConfigData, PropertyData
from tests.fixtures.dummy.facilities import BuildingData, RoomData
from tests.fixtures.dummy.finance import AccountData, SemesterData
from tests.fixtures.dummy.host import (
    IPData, SwitchPatchPortData,UserInterfaceData, UserHostData)
from tests.fixtures.dummy.net import SubnetData, VLANData
from tests.fixtures.dummy.property import TrafficGroupData
from tests.fixtures.dummy.user import UserData


class Test_010_User_Move(FixtureDataTestBase):
    datasets = (ConfigData, BuildingData, IPData, RoomData, SubnetData,
                SwitchPatchPortData, UserData, UserInterfaceData, UserHostData,
                VLANData)

    def setUp(self):
        super(Test_010_User_Move, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.dummy.login).one()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()
        self.old_room = self.user.room #building.Room.q.get(1)
        self.same_building = facilities.Building.q.filter_by(
            short_name=BuildingData.dummy_house1.short_name).one()
        assert self.same_building == self.old_room.building
        self.other_building = facilities.Building.q.filter_by(
            short_name=BuildingData.dummy_house2.short_name).one()

        self.new_room_other_building = facilities.Room.q.filter_by(
            building=self.other_building).one()
        self.new_room_same_building = facilities.Room.q.filter_by(
            building=self.same_building, number=RoomData.dummy_room3.number,
            level=RoomData.dummy_room3.level, inhabitable=True).one()
        self.new_switch_patch_port = PatchPort.q.filter_by(
            name=SwitchPatchPortData.dummy_patch_port2.name).one()

    def test_0010_moves_into_same_room(self):
        self.assertRaises(
            AssertionError, UserHelper.move, self.user, self.old_room.building,
            self.old_room.level, self.old_room.number, self.processing_user)

    def test_0020_moves_into_other_building(self):
        UserHelper.move(self.user, self.new_room_other_building.building,
            self.new_room_other_building.level,
            self.new_room_other_building.number, self.processing_user)
        self.assertEqual(self.user.room, self.new_room_other_building)
        self.assertEqual(self.user.user_hosts[0].room, self.new_room_other_building)
        #TODO test for changing ip


class Test_020_User_Move_In(FixtureDataTestBase):
    datasets = (AccountData, BuildingData, ConfigData, IPData, PropertyData,
                RoomData, SemesterData, SubnetData, SwitchPatchPortData,
                TrafficGroupData, UserData, UserHostData, UserInterfaceData,
                VLANData)

    def setUp(self):
        super(Test_020_User_Move_In, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

    def test_0010_move_in(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = facilities.Building.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_building,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            moved_from_division=False,
            already_paid_semester_fee=False
        )

        self.assertEqual(new_user.name, test_name)
        self.assertEqual(new_user.login, test_login)
        self.assertEqual(new_user.email, test_email)
        self.assertEqual(new_user.room.building, test_building)
        self.assertEqual(new_user.room.number, "1")
        self.assertEqual(new_user.room.level, 1)

        user_host = host.UserHost.q.filter_by(owner=new_user).one()
        self.assertEqual(len(user_host.user_interfaces), 1)
        user_interface = user_host.user_interfaces[0]
        self.assertEqual(len(user_interface.ips), 1)
        user_ip = user_interface.ips[0]
        self.assertEqual(user_interface.mac, test_mac)

        # checks the initial group memberships
        active_user_groups = (new_user.active_property_groups() +
                              new_user.active_traffic_groups())
        for group in (config.member_group, config.network_access_group):
            self.assertIn(group, active_user_groups)

        self.assertTrue(UserHelper.has_network_access(new_user))
        self.assertIsNotNone(new_user.account)
        self.assertEqual(new_user.account.balance,
                         (SemesterData.dummy_semester1.registration_fee +
                          SemesterData.dummy_semester1.regular_semester_fee))
        self.assertFalse(new_user.has_property("reduced_semester_fee"))
        self.assertTrue(new_user.unix_account is not None)
        account = new_user.unix_account
        self.assertTrue(account.home_directory.endswith(new_user.login))
        self.assertTrue(account.home_directory.startswith('/home/'))


class Test_030_User_Move_Out(FixtureDataTestBase):
    datasets = (AccountData, ConfigData, IPData, SemesterData,
                SwitchPatchPortData, TrafficGroupData)

    def setUp(self):
        super(Test_030_User_Move_Out, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

    def test_0030_move_out(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = facilities.Building.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_building,
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
        self.assertIsNotNone(new_user.account)


class Test_040_User_Edit_Name(FixtureDataTestBase):
    datasets = (ConfigData, BuildingData, RoomData, UserData)

    def setUp(self):
        super(Test_040_User_Edit_Name, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.dummy.login).one()

    def test_0010_correct_new_name(self):
        new_name = "A new name"
        self.assertNotEqual(new_name, self.user.name)
        UserHelper.edit_name(self.user, new_name, self.user)
        self.assertEqual(self.user.name, new_name)


class Test_050_User_Edit_Email(FixtureDataTestBase):
    datasets = (ConfigData, BuildingData, RoomData, UserData)

    def setUp(self):
        super(Test_050_User_Edit_Email, self).setUp()
        self.user = user.User.q.filter_by(
            login=UserData.dummy.login).one()

    def test_0010_correct_new_email(self):
        new_mail = "user@example.net"
        self.assertNotEqual(new_mail, self.user.email)
        UserHelper.edit_email(self.user, new_mail, self.user)
        self.assertEqual(self.user.email, new_mail)


class Test_070_User_Move_Out_Temporarily(FixtureDataTestBase):
    datasets = (AccountData, ConfigData, IPData, PropertyData,
                SemesterData, SwitchPatchPortData, TrafficGroupData)

    def setUp(self):
        super(Test_070_User_Move_Out_Temporarily, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

    def test_0010_move_out_temporarily(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = facilities.Building.q.first()
        test_mac = "12:11:11:11:11:11"

        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_building,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            moved_from_division=False,
            already_paid_semester_fee=False
        )
        session.session.commit()

        during = closedopen(session.utcnow(), None)
        self.assertFalse(new_user.has_property("reduced_semester_fee"))

        UserHelper.move_out_temporarily(new_user, "", self.processing_user,
                                        during)
        session.session.commit()

        # check for tmpAusgezogen group membership
        self.assertIn(new_user, config.away_group.active_users())
        self.assertIn(config.away_group, new_user.active_property_groups())
        self.assertTrue(new_user.has_property("reduced_semester_fee"))

        # check if user has no ips left
        for user_host in new_user.user_hosts:
            for interface in user_host.user_interfaces:
                self.assertEqual(interface.ips, [])

        # check log message
        log_entry = new_user.log_entries[-1]
        self.assertAlmostEqual(log_entry.created_at, during.begin,
                               delta=timedelta(seconds=1))
        self.assertEqual(log_entry.author, self.processing_user)


class Test_080_User_Block(FixtureDataTestBase):
    datasets = (ConfigData, BuildingData, PropertyData, RoomData, UserData)

    def test_0010_user_has_no_network_access(self):
        u = user.User.q.filter_by(login=UserData.dummy.login).one()
        verstoss = PropertyGroup.q.filter(
            PropertyGroup.name == u"Verstoß").first()
#       Ich weiß nicht, ob dieser Test noch gebraucht wird!
#       self.assertTrue(u.has_property("network_access"))
        self.assertNotIn(verstoss, u.active_property_groups())

        blocked_user = UserHelper.suspend(u, u"test", u)
        session.session.commit()

        self.assertFalse(blocked_user.has_property("network_access"))
        self.assertIn(verstoss, blocked_user.active_property_groups())

        self.assertEqual(blocked_user.log_entries[0].author, u)


class Test_090_User_Is_Back(FixtureDataTestBase):
    datasets = (ConfigData, IPData, PropertyData, SwitchPatchPortData, UserData)

    def setUp(self):
        super(Test_090_User_Is_Back, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()
        self.user = user.User.q.filter_by(login=UserData.dummy.login).one()
        UserHelper.move_out_temporarily(user=self.user, comment='',
                                        processor=self.processing_user)
        session.session.commit()

    def test_0010_user_is_back(self):
        self.assertTrue(self.user.has_property("reduced_semester_fee"))
        UserHelper.is_back(self.user, self.processing_user)
        session.session.commit()

        # check whether user has at least one ip
        self.assertNotEqual(self.user.user_hosts[0].user_interfaces[0].ips, [])

        # check log message
        log_entry = self.user.log_entries[-1]
        self.assertAlmostEqual(log_entry.created_at, session.utcnow(),
                               delta=timedelta(seconds=5))
        self.assertEqual(log_entry.author, self.processing_user)

        self.assertFalse(self.user.has_property("reduced_semester_fee"))
