# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from tests import FixtureDataTestBase
from tests.lib.fixtures.host_fixtures import UserNetDeviceData, UserData,\
    UserHostData, RoomData, ServerHostData, ServerNetDeviceData,\
    SwitchPortData, SwitchData, SwitchNetDeviceData, IpData, SubnetData

from pycroft.lib.host import change_mac, create_user_host, delete_user_host,\
    create_server_host, delete_server_host, create_user_net_device,\
    delete_user_net_device, create_server_net_device, delete_server_net_device, \
    create_switch, delete_switch, create_switch_net_device, \
    delete_switch_net_device, create_ip, delete_ip

from pycroft.model import session
from pycroft.model.host import UserNetDevice, UserHost, ServerHost,\
    ServerNetDevice, Switch, SwitchNetDevice, Ip
from pycroft.model.dormitory import Room, Subnet
from pycroft.model.port import SwitchPort
from pycroft.model.user import User
from pycroft.model.logging import LogEntry


class Test_005_change_mac_net_device(FixtureDataTestBase):
    datasets = [UserNetDeviceData, UserData]

    def tearDown(self):
        LogEntry.q.delete()
        session.session.commit()
        super(Test_005_change_mac_net_device, self).tearDown()

    def test_0010_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        netdev = UserNetDevice.q.get(UserNetDeviceData.dummy_user_device1.id)
        user = User.q.get(UserData.dummy_user1.id)
        change_mac(netdev, new_mac, user)
        self.assertEqual(netdev.mac, new_mac)


class Test_010_UserHost(FixtureDataTestBase):
    datasets = [UserHostData, UserData, RoomData]

    def test_0010_create_user_host(self):
        room = Room.q.get(RoomData.dummy_room1.id)
        user = User.q.get(UserData.dummy_user1.id)

        new_user_host = create_user_host(user=user, room=room)

        self.assertIsNotNone(UserHost.q.get(new_user_host.id))

        db_user_host = UserHost.q.get(new_user_host.id)

        self.assertEqual(db_user_host.user, user)
        self.assertEqual(db_user_host.room, room)

        session.session.delete(db_user_host)
        session.session.commit()

    def test_0020_delete_user_host(self):
        del_user_host = delete_user_host(UserHostData.dummy_user_host1.id)

        self.assertIsNone(UserHost.q.get(del_user_host.id))

    def test_0025_delete_wrong_user_host(self):
        self.assertRaises(ValueError, delete_user_host,
            UserHostData.dummy_user_host1.id + 100)


class Test_020_ServerHost(FixtureDataTestBase):
    datasets = [ServerHostData, RoomData, UserData]

    def test_0010_create_server_host(self):
        room = Room.q.get(RoomData.dummy_room1.id)
        user = User.q.get(UserData.dummy_user1.id)

        new_server_host = create_server_host(room=room, user=user)

        self.assertIsNotNone(ServerHost.q.get(new_server_host.id))

        db_server_host = ServerHost.q.get(new_server_host.id)

        self.assertEqual(db_server_host.room, room)
        self.assertEqual(db_server_host.user, user)

        session.session.delete(db_server_host)
        session.session.commit()

    def test_0020_delete_server_host(self):
        del_server_host = delete_server_host(
            ServerHostData.dummy_server_host1.id)

        self.assertIsNone(ServerHost.q.get(del_server_host.id))

    def test_0025_delete_wrong_server_host(self):
        self.assertRaises(ValueError, delete_server_host,
            ServerHostData.dummy_server_host1.id + 100)


class Test_030_Switch(FixtureDataTestBase):

    datasets = [SwitchData, UserData, RoomData]

    def test_0010_create_switch(self):
        user = User.q.get(UserData.dummy_user1.id)
        room = Room.q.get(RoomData.dummy_room1.id)
        name = "dummy_switch2"
        management_ip = "141.30.216.16"

        switch =  create_switch(user=user, room=room, name=name,
            management_ip=management_ip)

        self.assertIsNotNone(Switch.q.get(switch.id))

        db_switch =  Switch.q.get(switch.id)

        self.assertEqual(db_switch.user, user)
        self.assertEqual(db_switch.room, room)
        self.assertEqual(db_switch.name, name)
        self.assertEqual(db_switch.management_ip, management_ip)

        session.session.delete(db_switch)
        session.session.commit()

    def test_0020_delete_switch(self):
        del_switch =  delete_switch(SwitchData.dummy_switch1.id)

        self.assertIsNone(Switch.q.get(del_switch.id))

    def test_0025_delete_wrong_switch(self):
        self.assertRaises(ValueError, delete_switch,
            SwitchData.dummy_switch1.id + 100)


class Test_040_UserNetDevice(FixtureDataTestBase):

    datasets = [UserNetDeviceData, UserHostData]

    def test_0010_create_user_net_device(self):
        host = UserHost.q.get(UserHostData.dummy_user_host1.id)

        user_net_device = create_user_net_device(mac="00:00:00:00:00:00",
            host=host)

        self.assertIsNotNone(UserNetDevice.q.get(user_net_device.id))

        db_user_net_device = UserNetDevice.q.get(user_net_device.id)

        self.assertEqual(db_user_net_device.mac, "00:00:00:00:00:00")
        self.assertEqual(db_user_net_device.host, host)

        session.session.delete(db_user_net_device)
        session.session.commit()

    def test_0020_delete_user_net_device(self):
        del_user_net_device = delete_user_net_device(
            UserNetDeviceData.dummy_user_device1.id)

        self.assertIsNone(UserNetDevice.q.get(
            UserNetDeviceData.dummy_user_device1.id))

    def test_0025_delete_wrong_user_net_device(self):
        self.assertRaises(ValueError, delete_user_net_device,
            UserNetDeviceData.dummy_user_device1.id + 100)


class Test_050_ServerNetDevice(FixtureDataTestBase):
    datasets = [ServerNetDeviceData, ServerHostData, SwitchPortData]

    def test_0010_create_server_net_device(self):
        host = ServerHost.q.get(ServerHostData.dummy_server_host1.id)
        switch_port = SwitchPort.q.get(SwitchPortData.dummy_switch_port1.id)

        server_net_device = create_server_net_device(mac="00:00:00:00:00:00",
            host=host, switch_port=switch_port)

        self.assertIsNotNone(ServerNetDevice.q.get(server_net_device.id))

        db_server_net_device = ServerNetDevice.q.get(server_net_device.id)

        self.assertEqual(db_server_net_device.mac, "00:00:00:00:00:00")
        self.assertEqual(db_server_net_device.host, host)
        self.assertEqual(db_server_net_device.switch_port, switch_port)

        session.session.delete(db_server_net_device)
        session.session.commit()

    def test_0020_delete_server_net_device(self):
        del_server_net_device = delete_server_net_device(
            ServerNetDeviceData.dummy_server_device1.id)

        self.assertIsNone(ServerNetDevice.q.get(del_server_net_device.id))

    def test_0025_delete_wrong_server_net_device(self):
        self.assertRaises(ValueError, delete_server_net_device,
            ServerNetDeviceData.dummy_server_device1.id + 100)

class Test_060_SwitchNetDevice(FixtureDataTestBase):

    datasets = [SwitchNetDeviceData, SwitchData]

    def test_0010_create_switch_net_device(self):
        host =  Switch.q.get(SwitchData.dummy_switch1.id)
        mac = "00:00:00:00:00:00"

        switch_net_device = create_switch_net_device(mac=mac, host=host)

        self.assertIsNotNone(SwitchNetDevice.q.get(switch_net_device.id))

        db_switch_net_device = SwitchNetDevice.q.get(switch_net_device.id)

        self.assertEqual(db_switch_net_device.mac, mac)
        self.assertEqual(db_switch_net_device.host, host)

        session.session.delete(db_switch_net_device)
        session.session.commit()

    def test_0020_delete_switch_net_device(self):
        del_switch_net_device =  delete_switch_net_device(
            SwitchNetDeviceData.dummy_switch_device1.id)

        self.assertIsNone(SwitchNetDevice.q.get(del_switch_net_device.id))

    def test_0025_delete_wrong_switch_net_device(self):
        self.assertRaises(ValueError, delete_switch_net_device,
            SwitchNetDeviceData.dummy_switch_device1.id + 100)

class Test_070_Ip(FixtureDataTestBase):

    datasets = [IpData, SubnetData, SwitchNetDeviceData]

    def test_0010_create_ip(self):
        address = "141.30.216.16"
        net_device = SwitchNetDevice.q.get(
            SwitchNetDeviceData.dummy_switch_device1.id)
        subnet = Subnet.q.get(SubnetData.dummy_subnet1.id)

        ip = create_ip(address=address, net_device=net_device, subnet=subnet)

        self.assertIsNotNone(Ip.q.get(ip.id))

        db_ip =  Ip.q.get(ip.id)

        self.assertEqual(db_ip.address, address)
        self.assertEqual(db_ip.net_device, net_device)
        self.assertEqual(db_ip.subnet, subnet)

        session.session

    def test_0020_delete_ip(self):
        del_ip = delete_ip(IpData.dummy_ip1.id)

        self.assertIsNone(Ip.q.get(del_ip.id))

    def test_delete_wrong_ip(self):
        self.assertRaises(ValueError, delete_ip, IpData.dummy_ip1.id + 100)
