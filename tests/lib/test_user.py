# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta

from pycroft.lib.facilities import get_room
from pycroft.lib.user import move, move_out, move_in
from tests.factories import UserWithHostFactory, MembershipFactory, UserFactory, RoomFactory, \
    ConfigFactory

from pycroft import config
from pycroft.helpers.i18n import localized
from pycroft.helpers.interval import closedopen
from pycroft.lib import user as UserHelper
from pycroft.model import (
    user, facilities, session, host)
from pycroft.model.port import PatchPort
from tests import FixtureDataTestBase, FactoryWithConfigDataTestBase, FactoryDataTestBase
from tests.factories.address import AddressFactory
from tests.fixtures import network_access
from tests.fixtures.config import ConfigData, PropertyData
from tests.fixtures.dummy.facilities import BuildingData, RoomData
from tests.fixtures.dummy.finance import AccountData
from tests.fixtures.dummy.host import (
    IPData, PatchPortData, InterfaceData, HostData)
from tests.fixtures.dummy.net import SubnetData, VLANData
from tests.fixtures.dummy.user import UserData

from .. import factories


class Test_User_Move(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        # we just create the subnet to ensure it stays the same when in the same building
        subnet = factories.SubnetFactory()
        self.user = UserWithHostFactory(
            room__patched_with_subnet=True,
            room__patch_ports__switch_port__default_vlans__subnets=[subnet]
        )
        self.processing_user = UserFactory()
        self.old_room = self.user.room
        assert all(h.room == self.old_room for h in self.user.hosts)
        self.new_room_other_building = factories.RoomFactory(patched_with_subnet=True)
        self.new_room_same_building = factories.RoomFactory(
            building=self.old_room.building,
            patched_with_subnet=True,
            patch_ports__switch_port__default_vlans__subnets=[subnet],
        )

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


class Test_User_Move_In(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.config = factories.ConfigFactory()
        self.room = factories.RoomFactory(level=1, number="1", patched_with_subnet=True)
        self.processing_user = UserFactory()

    def setUp(self):
        super().setUp()
        class _UserData:
            name = u"Hans"
            login = u"hans66"
            email = u"hans@hans.de"
            mac = "12:11:11:11:11:11"
            birthdate = "1990-01-01"
        self.user = _UserData

    def create_some_user(self):
        new_user, _ = UserHelper.create_user(
            self.user.name,
            self.user.login,
            self.user.email,
            self.user.birthdate,
            processor=self.processing_user,
            groups=[self.config.member_group],
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
        self.assert_membership_groups(new_user.active_memberships(), [self.config.member_group])
        self.assertEqual(new_user.unix_account.home_directory, f"/home/{new_user.login}")
        self.assertEqual(len(new_user.log_entries), 2)
        first, second = new_user.log_entries
        self.assert_logmessage_startswith(first, "Added to group Mitglied")
        self.assert_logmessage_startswith(second, "User created")

    def test_0010_move_in(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = self.room.building
        test_mac = "12:11:11:11:11:11"
        test_birthdate = "1990-01-01"

        address = get_room(building_id=test_building.id, level=1, room_number="1").address
        new_user, _ = UserHelper.create_user(
            test_name,
            test_login,
            test_email,
            test_birthdate,
            processor=self.processing_user,
            groups=[self.config.member_group],
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
        for group in {self.config.member_group, self.config.network_access_group}:
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


class Test_User_Move_Out_And_Back_In(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.config = factories.ConfigFactory()
        self.room = factories.RoomFactory(patched_with_subnet=True, number="1", level=1)
        self.processing_user = UserFactory()

    def test_move_out(self):
        test_name = u"Hans"
        test_login = u"hans66"
        test_email = u"hans@hans.de"
        test_building = self.room.building
        test_mac = "12:11:11:11:11:11"
        test_birthdate = "1990-01-01"

        address = self.room.address

        new_user, _ = UserHelper.create_user(
            test_name,
            test_login,
            test_email,
            test_birthdate,
            processor=self.processing_user,
            groups=[self.config.member_group],
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


class UserRoomHistoryTestCase(FactoryDataTestBase):
    def create_factories(self):
        ConfigFactory.create()

        self.processor = UserFactory.create()

        self.user = UserFactory()
        self.user_no_room = UserFactory(room=None, address=AddressFactory())
        self.room = RoomFactory()

    def test_room_history_create(self):
        self.assertEqual(1, len(self.user.room_history_entries), "more than one room history entry")

        rhe = self.user.room_history_entries[0]

        self.assertEqual(self.user.room, rhe.room)
        self.assertIsNotNone(rhe.begins_at)
        self.assertIsNone(rhe.ends_at)

    def test_room_history_move(self):
        session.session.refresh(self.room)

        old_room = self.user.room

        move(self.user, self.room.building_id, self.room.level, self.room.number, self.processor)

        found_old = False
        found_new = False

        for rhe in self.user.room_history_entries:
            self.assertIsNotNone(rhe.begins_at)

            if rhe.room == old_room:
                self.assertIsNotNone(rhe.ends_at)
                found_old = True
            elif rhe.room == self.room:
                self.assertIsNone(rhe.ends_at)
                found_new = True

        self.assertTrue(found_new, "Did not find new history entry")
        self.assertTrue(found_old, "Did not find old history entry")

    def test_room_history_move_out(self):
        move_out(self.user, comment="test", processor=self.processor, when=session.utcnow())

        session.session.commit()

        rhe = self.user.room_history_entries[0]

        self.assertIsNotNone(rhe.begins_at)
        self.assertIsNotNone(rhe.ends_at)

    def test_room_history_move_in(self):
        self.assertEqual(0, len(self.user_no_room.room_history_entries))

        move_in(self.user_no_room, self.room.building.id, self.room.level, self.room.number,
                mac=None, processor=self.processor)

        session.session.commit()

        rhe = self.user_no_room.room_history_entries[0]

        self.assertEqual(rhe.room, self.room)

        self.assertIsNotNone(rhe.begins_at)
        self.assertIsNone(rhe.ends_at)

