# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta
from functools import partial

from pycroft.model.port import PatchPort
from pycroft.model.user import Membership, PropertyGroup
from tests import FixtureDataTestBase
from pycroft import config
from pycroft.helpers.interval import closedopen, single
from pycroft.lib import user as UserHelper, traffic
from pycroft.model import (
    user, facilities, session, logging, finance, host)
from tests.fixtures import network_access
from tests.fixtures.config import ConfigData, PropertyData
from tests.fixtures.dummy.facilities import BuildingData, RoomData
from tests.fixtures.dummy.finance import AccountData, SemesterData
from tests.fixtures.dummy.host import (
    IPData, SwitchPatchPortData,UserInterfaceData, UserHostData)
from tests.fixtures.dummy.net import SubnetData, VLANData
from tests.fixtures.dummy.property import TrafficGroupData
from tests.fixtures.dummy.user import UserData
from tests.fixtures import user_with_trafficgroups


class Test_010_User_Move(FixtureDataTestBase):
    datasets = (ConfigData, BuildingData, IPData, RoomData, SubnetData,
                SwitchPatchPortData, UserData, UserInterfaceData, UserHostData,
                VLANData, TrafficGroupData)

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
        # whether old traffic groups get deleted is untested,
        # because adding a `default_traffic_group` is hard with our
        # fixture setup

        traffic_group = user.TrafficGroup.q.first()
        UserHelper.move(
            self.user, self.new_room_other_building.building,
            self.new_room_other_building.level,
            self.new_room_other_building.number, self.processing_user,
            traffic_group_id=traffic_group.id,
        )
        self.assertEqual(self.user.room, self.new_room_other_building)
        self.assertEqual(self.user.user_hosts[0].room, self.new_room_other_building)
        self.assertIn(traffic_group, self.user.active_traffic_groups())
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
        for group in {config.member_group, config.network_access_group}:
            self.assertIn(group, active_user_groups)

        # our fixtures don't have a default traffic group for our
        # building, so we test that separately
        traffic_group = user.TrafficGroup.q.one()
        self.assertNotIn(traffic_group, active_user_groups)

        self.assertTrue(UserHelper.has_network_access(new_user))
        self.assertIsNotNone(new_user.account)
        self.assertEqual(new_user.account.balance, 0)
        self.assertFalse(new_user.has_property("reduced_semester_fee"))
        self.assertTrue(new_user.unix_account is not None)
        account = new_user.unix_account
        self.assertTrue(account.home_directory.endswith(new_user.login))
        self.assertTrue(account.home_directory.startswith('/home/'))

    def test_move_in_custom_traffic_group(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = facilities.Building.q.first()
        test_mac = "12:11:11:11:11:11"

        traffic_group = user.TrafficGroup.q.first()
        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_building,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            traffic_group_id=traffic_group.id,
        )
        self.assertIn(traffic_group, new_user.active_traffic_groups())



class Test_030_User_Move_Out_And_Back_In(FixtureDataTestBase):
    datasets = (AccountData, ConfigData, IPData, SemesterData,
                SwitchPatchPortData, TrafficGroupData)

    def setUp(self):
        super().setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

    def test_0030_move_out(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = facilities.Building.q.first()
        test_mac = "12:11:11:11:11:11"
        traffic_group = user.TrafficGroup.q.first()

        new_user = UserHelper.move_in(
            test_name,
            test_login,
            test_email,
            test_building,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            traffic_group_id=traffic_group.id,
        )
        session.session.commit()

        out_time = session.utcnow()

        UserHelper.move_out(user=new_user, comment="",
                            processor=self.processing_user, when=out_time)

        session.session.refresh(new_user)
        # check ends_at of moved out user
        for membership in new_user.memberships:
            self.assertIsNotNone(membership.ends_at)
            self.assertLessEqual(membership.ends_at, out_time)

        self.assertFalse(new_user.user_hosts)
        self.assertIsNone(new_user.room)

        # check if users finance account still exists
        self.assertIsNotNone(new_user.account)

        UserHelper.move_back_in(
            user=new_user,
            building=test_building,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
            traffic_group_id=traffic_group.id,
        )

        session.session.refresh(new_user)
        self.assertEqual(new_user.room.building, test_building)
        self.assertEqual(new_user.room.level, 1)
        self.assertEqual(new_user.room.number, "1")

        self.assertEqual(len(new_user.user_hosts), 1)
        user_host = new_user.user_hosts[0]
        self.assertEqual(len(user_host.user_interfaces), 1)
        self.assertEqual(user_host.user_interfaces[0].mac, test_mac)
        self.assertEqual(len(user_host.ips), 1)

        self.assertTrue(new_user.member_of(config.member_group))
        self.assertTrue(new_user.member_of(config.network_access_group))
        # `member_of` only concerns `PropertyGroup`s!
        self.assertIn(traffic_group, new_user.active_traffic_groups())


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


class UserWithNetworkAccessTestCase(FixtureDataTestBase):
    # config with properties and a dummy user with network access
    datasets = (ConfigData, PropertyData, network_access.MembershipData)

    def setUp(self):
        super().setUp()
        self.user_to_block = user.User.q.filter_by(login=UserData.dummy.login).one()
        # these asserts verify correct initial state of the fixtures
        self.assertTrue(self.user_to_block.has_property("network_access"))
        verstoss = config.violation_group
        self.assertNotIn(verstoss, self.user_to_block.active_property_groups())

    def assert_violation_membership(self, user, subinterval=None):
        if subinterval is None:
            self.assertFalse(user.has_property("network_access"))
            self.assertTrue(user.member_of(config.violation_group))
            return

        self.assertTrue(user.member_of(config.violation_group, when=subinterval))

    def assert_no_violation_membership(self, user, subinterval=None):
        if subinterval is None:
            self.assertTrue(user.has_property("network_access"))
            self.assertFalse(user.member_of(config.violation_group))
            return

        self.assertFalse(user.member_of(config.violation_group, when=subinterval))

    def test_instant_user_blocking_and_unblocking(self):
        # TODO: test for log entries
        u = self.user_to_block

        blocked_user = UserHelper.suspend(u, reason=u"test", processor=u)
        session.session.commit()
        blocked_during = single(session.utcnow())

        self.assertEqual(u.log_entries[0].author, blocked_user)
        self.assert_violation_membership(blocked_user)
        self.assert_violation_membership(blocked_user, subinterval=blocked_during)

        unblocked_user = UserHelper.unblock(blocked_user, processor=u)
        session.session.commit()

        self.assertEqual(u.log_entries[0].author, unblocked_user)
        self.assert_violation_membership(unblocked_user, subinterval=blocked_during)

    def test_deferred_blocking_and_unblocking_works(self):
        u = self.user_to_block

        blockage = session.utcnow() + timedelta(days=1)
        unblockage = blockage + timedelta(days=2)
        blocked_user = UserHelper.suspend(u, reason=u"test", processor=u,
                                          during=closedopen(blockage, None))
        session.session.commit()

        blocked_during = closedopen(blockage, unblockage)
        self.assertEqual(u.log_entries[0].author, blocked_user)
        self.assert_violation_membership(blocked_user, subinterval=blocked_during)

        unblocked_user = UserHelper.unblock(blocked_user, processor=u, when=unblockage)
        session.session.commit()

        self.assertEqual(unblocked_user.log_entries[0].author, unblocked_user)
        self.assert_violation_membership(unblocked_user, subinterval=blocked_during)


class TrafficGroupTestCase(FixtureDataTestBase):
    datasets = frozenset(user_with_trafficgroups.datasets)

    def setUp(self):
        super().setUp()
        self.user = user.User.q.filter_by(login='test').one()
        self.user2 = user.User.q.filter_by(login='test2').one()
        self.traffic_group = user.TrafficGroup.q.first()
        self.traffic_group2 = user.TrafficGroup.q.filter_by(name='non_default').one()

    def test_determine_traffic_group_default(self):
        self.assertEqual(traffic.determine_traffic_group(self.user),
                         self.traffic_group)

    def test_determine_traffic_group_building_has_no_default(self):
        group = traffic.determine_traffic_group(self.user2)
        self.assertEqual(group, None)

    def test_determine_traffic_group_uses_explicit_group(self):
        group = traffic.determine_traffic_group(self.user2, self.traffic_group2.id)
        self.assertEqual(group, self.traffic_group2)

    def test_determine_traffic_group_prefers_explicit_group(self):
        group = traffic.determine_traffic_group(self.user, self.traffic_group2.id)
        self.assertEqual(group, self.traffic_group2)

    def test_setup_traffic_group(self):
        setup = partial(traffic.setup_traffic_group, processor=self.user2)

        setup(self.user)
        session.session.refresh(self.user)
        groups = self.user.active_traffic_groups()
        self.assertIn(self.traffic_group, groups)
        self.assertNotIn(self.traffic_group2, groups)

        setup(self.user, custom_group_id=self.traffic_group2.id)
        session.session.refresh(self.user)
        groups = self.user.active_traffic_groups()
        self.assertIn(self.traffic_group, groups)
        self.assertIn(self.traffic_group2, groups)

        setup(self.user, custom_group_id=self.traffic_group2.id, terminate_other=True)
        session.session.refresh(self.user)
        groups = self.user.active_traffic_groups()
        self.assertNotIn(self.traffic_group, groups)
        self.assertIn(self.traffic_group2, groups)

    def test_setup_traffic_group_no_group(self):
        traffic.setup_traffic_group(self.user2, processor=self.user2)
        session.session.refresh(self.user2)
        # expect an empty list
        self.assertFalse(self.user.active_traffic_groups())
