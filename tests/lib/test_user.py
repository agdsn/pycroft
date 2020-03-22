# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.lib.facilities import get_room
from tests.factories import UserWithHostFactory, MembershipFactory, UserFactory, RoomFactory

from pycroft import config
from pycroft.helpers.i18n import localized
from pycroft.helpers.interval import closedopen
from pycroft.lib import user as UserHelper
from pycroft.model import (
    user, facilities, session, host)
from pycroft.model.port import PatchPort
from tests import FixtureDataTestBase, FactoryWithConfigDataTestBase
from tests.factories.address import AddressFactory
from tests.fixtures import network_access
from tests.fixtures.config import ConfigData, PropertyData
from tests.fixtures.dummy.facilities import BuildingData, RoomData
from tests.fixtures.dummy.finance import AccountData
from tests.fixtures.dummy.host import (
    IPData, PatchPortData, InterfaceData, HostData)
from tests.fixtures.dummy.net import SubnetData, VLANData
from tests.fixtures.dummy.user import UserData


class Test_010_User_Move(FixtureDataTestBase):
    datasets = (ConfigData, BuildingData, IPData, RoomData, SubnetData,
                PatchPortData, UserData, InterfaceData, HostData,
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
            name=PatchPortData.dummy_patch_port2.name).one()

    def test_0010_moves_into_same_room(self):
        self.assertRaises(
            AssertionError, UserHelper.move, self.user, self.old_room.building.id,
            self.old_room.level, self.old_room.number, self.processing_user)

    def test_0020_moves_into_other_building(self):
        UserHelper.move(
            self.user, self.new_room_other_building.building.id,
            self.new_room_other_building.level,
            self.new_room_other_building.number, self.processing_user,
        )
        self.assertEqual(self.user.room, self.new_room_other_building)
        self.assertEqual(self.user.hosts[0].room, self.new_room_other_building)
        # TODO test for changing ip


class Test_020_User_Move_In(FixtureDataTestBase):
    datasets = (AccountData, BuildingData, ConfigData, IPData, PropertyData,
                RoomData, SubnetData, PatchPortData,
                UserData, HostData, InterfaceData, VLANData)

    def setUp(self):
        super(Test_020_User_Move_In, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.privileged.login).one()

        class _UserData:
            name = u"Hans"
            login = u"hans66"
            email = u"hans@hans.de"
            mac = "12:11:11:11:11:11"
            birthdate = "1990-01-01"
        self.user = _UserData
        self.room = facilities.Room.q.first()

    def create_some_user(self):
        new_user, _ = UserHelper.create_user(
            self.user.name,
            self.user.login,
            self.user.email,
            self.user.birthdate,
            processor=self.processing_user,
            groups=[config.member_group],
            address=self.room.address,
        )
        return new_user

    def assert_account_name(self, account, expected_name):
        self.assertEqual(localized(account.name, {int: {'insert_commas': False}}),
                         expected_name)

    def assert_membership_groups(self, memberships, expected_groups):
        self.assertEqual(len(memberships), len(expected_groups))
        self.assertEqual({m.group for m in memberships},
                         set(expected_groups))

    def assert_logmessage_startswith(self, logentry, expected_start: str):
        self.assertTrue(localized(logentry.message), expected_start)

    def test_user_create(self):
        new_user = self.create_some_user()
        self.assertEqual(new_user.name, self.user.name)
        self.assertEqual(new_user.login, self.user.login)
        self.assertEqual(new_user.email, self.user.email)
        # TODO fix signature and check for explicitly supplied address.
        # self.assertEqual(new_user.address, config.dummy_address)
        self.assert_account_name(new_user.account, f"User {new_user.id}")
        self.assert_membership_groups(new_user.active_memberships(), [config.member_group])
        self.assertEqual(new_user.unix_account.home_directory, f"/home/{new_user.login}")
        self.assertEqual(len(new_user.log_entries), 2)
        first, second = new_user.log_entries
        self.assert_logmessage_startswith(first, "Added to group Mitglied")
        self.assert_logmessage_startswith(second, "User created")

    def test_0010_move_in(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = facilities.Building.q.first()
        test_mac = "12:11:11:11:11:11"
        test_birthdate = "1990-01-01"

        address = get_room(building_id=test_building.id, level=1, room_number="1").address
        new_user, _ = UserHelper.create_user(
            test_name,
            test_login,
            test_email,
            test_birthdate,
            processor=self.processing_user,
            groups=[config.member_group],
            address=address
        )

        UserHelper.move_in(
            new_user,
            building_id=test_building.id,
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
        self.assertEqual(new_user.address, new_user.room.address)

        user_host = host.Host.q.filter_by(owner=new_user).one()
        self.assertEqual(len(user_host.interfaces), 1)
        user_interface = user_host.interfaces[0]
        self.assertEqual(len(user_interface.ips), 1)
        self.assertEqual(user_interface.mac, test_mac)

        # checks the initial group memberships
        active_user_groups = new_user.active_property_groups()
        for group in {config.member_group, config.network_access_group}:
            self.assertIn(group, active_user_groups)

        self.assertIsNotNone(new_user.account)
        self.assertEqual(new_user.account.balance, 0)
        self.assertFalse(new_user.has_property("reduced_membership_fee"))
        self.assertTrue(new_user.unix_account is not None)
        account = new_user.unix_account
        self.assertTrue(account.home_directory.endswith(new_user.login))
        self.assertTrue(account.home_directory.startswith('/home/'))


class MovedInUserTestCase(FactoryWithConfigDataTestBase):
    def create_factories(self):
        # We want a user who lives somewhere with a membership!
        super().create_factories()
        self.processor = UserFactory.create()
        self.user = UserWithHostFactory.create()
        self.membership = MembershipFactory.create(user=self.user,
                                                   group=self.config.member_group)
        self.other_room = RoomFactory.create()

    def move_out(self, user, comment=None):
        UserHelper.move_out(user, comment=comment or "", processor=self.processor,
                            when=session.utcnow())
        session.session.refresh(user)

    def customize_address(self, user):
        self.user.address = address = AddressFactory.create(city="Bielefeld")
        session.session.add(user)
        session.session.commit()
        self.assertTrue(user.has_custom_address)
        return address

    def test_move_out_keeps_address(self):
        self.assertFalse(self.user.has_custom_address)
        old_address = self.user.address

        self.move_out(self.user)
        self.assertEqual(self.user.active_memberships(), [])
        self.assertIsNone(self.user.room)
        self.assertEqual(self.user.address, old_address)

    def test_move_out_keeps_custom_address(self):
        address = self.customize_address(self.user)
        self.move_out(self.user)
        self.assertEqual(self.user.address, address)

    def move(self, user, room):
        UserHelper.move(user, processor=self.processor,
                        building_id=room.building_id, level=room.level, room_number=room.number)
        session.session.refresh(user)

    def test_move_changes_address(self):
        self.move(self.user, self.other_room)
        self.assertEqual(self.user.address, self.other_room.address)

    def test_move_keeps_custom_address(self):
        address = self.customize_address(self.user)
        self.move(self.user, self.other_room)
        self.assertEqual(self.user.address, address)


class Test_030_User_Move_Out_And_Back_In(FixtureDataTestBase):
    datasets = (AccountData, ConfigData, IPData, PatchPortData)

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
        test_birthdate = "1990-01-01"

        address = get_room(building_id=test_building.id, level=1, room_number="1").address

        new_user, _ = UserHelper.create_user(
            test_name,
            test_login,
            test_email,
            test_birthdate,
            processor=self.processing_user,
            groups=[config.member_group],
            address=address
        )

        UserHelper.move_in(
            new_user,
            building_id=test_building.id,
            level=1,
            room_number="1",
            mac=test_mac,
            processor=self.processing_user,
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

        self.assertFalse(new_user.hosts)
        self.assertIsNone(new_user.room)
        # move_out keeps user's address
        self.assertEquals(new_user.address, address)

        # check if users finance account still exists
        self.assertIsNotNone(new_user.account)

        UserHelper.move_in(
            user=new_user,
            building_id=test_building.id,
            level=1,
            room_number="1",
            mac=test_mac,
            birthdate=test_birthdate,
            processor=self.processing_user,
        )

        session.session.refresh(new_user)
        self.assertEqual(new_user.room.building, test_building)
        self.assertEqual(new_user.room.level, 1)
        self.assertEqual(new_user.room.number, "1")
        self.assertEqual(new_user.address, new_user.room.address)

        self.assertEqual(len(new_user.hosts), 1)
        user_host = new_user.hosts[0]
        self.assertEqual(len(user_host.interfaces), 1)
        self.assertEqual(user_host.interfaces[0].mac, test_mac)
        self.assertEqual(len(user_host.ips), 1)

        self.assertTrue(new_user.member_of(config.member_group))
        self.assertTrue(new_user.member_of(config.network_access_group))


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

    def test_deferred_blocking_and_unblocking_works(self):
        u = self.user_to_block

        blockage = session.utcnow() + timedelta(days=1)
        unblockage = blockage + timedelta(days=2)
        blocked_user = UserHelper.block(u, reason=u"test", processor=u,
                                        during=closedopen(blockage, None))
        session.session.commit()

        blocked_during = closedopen(blockage, unblockage)
        self.assertEqual(u.log_entries[0].author, blocked_user)
        self.assert_violation_membership(blocked_user, subinterval=blocked_during)

        unblocked_user = UserHelper.unblock(blocked_user, processor=u, when=unblockage)
        session.session.commit()

        self.assertEqual(unblocked_user.log_entries[0].author, unblocked_user)
        self.assert_violation_membership(unblocked_user, subinterval=blocked_during)
