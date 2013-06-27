# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from tests import FixtureDataTestBase
from tests.lib.fixtures.dormitory_fixtures import DormitoryData, RoomData,\
    SubnetData, VLanData

from pycroft.model.dormitory import Dormitory, Room, Subnet, VLan
from pycroft.lib.dormitory import create_dormitory, create_room,\
    delete_dormitory, delete_room, create_subnet, delete_subnet, create_vlan,\
    delete_vlan
from pycroft.model import session

class Test_010_Dormitory(FixtureDataTestBase):
    datasets = [DormitoryData]

    def test_0010_create_dormitory(self):
        new_dormitory = create_dormitory(number="101", short_name="wu101",
            street="wundstrasse")

        self.assertIsNotNone(Dormitory.q.get(new_dormitory.id))

        db_dormitory = Dormitory.q.get(new_dormitory.id)

        self.assertEqual(db_dormitory.number, "101")
        self.assertEqual(db_dormitory.short_name, "wu101")
        self.assertEqual(db_dormitory.street, "wundstrasse")

        session.session.delete(db_dormitory)
        session.session.commit()

    def test_0020_delete_dormitory(self):
        del_dormitory = delete_dormitory(DormitoryData.dummy_dormitory1.id)

        self.assertIsNone(Dormitory.q.get(del_dormitory.id))

    def test_0025_delete_wrong_dormitory(self):
        # Try to delete a non existing dormitory
        self.assertRaises(ValueError, delete_dormitory,
            DormitoryData.dummy_dormitory1.id + 100)


class Test_020_Room(FixtureDataTestBase):
    datasets = [RoomData]

    def test_0010_create_room(self):
        dormitory = Dormitory.q.get(DormitoryData.dummy_dormitory1.id)
        new_room = create_room(number="102", level=0, inhabitable=True,
            dormitory=dormitory)

        self.assertIsNotNone(Room.q.get(new_room.id))

        db_room = Room.q.get(new_room.id)

        self.assertEqual(db_room.number, "102")
        self.assertEqual(db_room.level, 0)
        self.assertEqual(db_room.inhabitable, True)
        self.assertEqual(db_room.dormitory_id,
            DormitoryData.dummy_dormitory1.id)

        session.session.delete(db_room)
        session.session.commit()

    def test_0020_delete_room(self):
        del_room = delete_room(RoomData.dummy_room1.id)

        self.assertIsNone(Room.q.get(del_room.id))

    def test_0025_delete_wrong_room(self):
        # Try to delete a non existing room
        self.assertRaises(ValueError, delete_room,
            RoomData.dummy_room1.id + 100)


class Test_030_Subnet(FixtureDataTestBase):
    datasets = [SubnetData]

    def test_0010_create_subnet(self):
        new_subnet = create_subnet(address="192.168.2.1", gateway="192.168.2.1",
            dns_domain="dummy_domain", reserved_addresses=1, ip_type="4")

        self.assertIsNotNone(Subnet.q.get(new_subnet.id))

        db_subnet = Subnet.q.get(new_subnet.id)

        self.assertEqual(db_subnet.address, "192.168.2.1")
        self.assertEqual(db_subnet.gateway, "192.168.2.1")
        self.assertEqual(db_subnet.dns_domain, "dummy_domain")
        self.assertEqual(db_subnet.reserved_addresses, 1)
        self.assertEqual(db_subnet.ip_type, "4")

        session.session.delete(db_subnet)
        session.session.commit()

    def test_0020_delete_subnet(self):
        del_subnet = delete_subnet(SubnetData.dummy_subnet1.id)

        self.assertIsNone(Subnet.q.get(del_subnet.id))

    def test_0025_delete_wrong_subnet(self):
        self.assertRaises(ValueError, delete_subnet,
            SubnetData.dummy_subnet1.id + 100)


class Test_040_Vlan(FixtureDataTestBase):
    datasets = [VLanData]

    def test_0010_create_vlan(self):
        new_vlan = create_vlan(name="dummy_vlan2", tag=21)

        self.assertIsNotNone(VLan.q.get(new_vlan.id))

        db_vlan = VLan.q.get(new_vlan.id)

        self.assertEqual(db_vlan.name, "dummy_vlan2")
        self.assertEqual(db_vlan.tag, 21)

        session.session.delete(db_vlan)
        session.session.commit()

    def test_0020_delete_vlan(self):
        del_vlan = delete_vlan(VLanData.dummy_vlan1.id)

        self.assertIsNone(VLan.q.get(del_vlan.id))

    def test_0025_delete_wrong_vlan(self):
        self.assertRaises(ValueError, delete_vlan,
            VLanData.dummy_vlan1.id + 100)
