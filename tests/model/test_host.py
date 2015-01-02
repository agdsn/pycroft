# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re

from sqlalchemy.exc import IntegrityError

from pycroft.helpers.host import get_free_ip, MacExistsException
from pycroft.model import session, host, dormitory, user, accounting
from tests import FixtureDataTestBase
from tests.model.fixtures.host_fixtures import (
    DormitoryData, VLANData, SubnetData, RoomData, UserData, UserHostData,
    UserNetDeviceData, IpData, TrafficVolumeData)


class Test_010_NetDeviceValidators(FixtureDataTestBase):
    datasets = [UserData, UserNetDeviceData, UserHostData]

    def test_0010_mac_validate(self):
        mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")

        nd = host.UserNetDevice(host=host.UserHost.q.first())
        def set_mac(mac):
            nd.mac = mac

        def test_mac(mac):
            parts = mac.split(":")
            if len(mac) != 17 or len(parts) != 6:
                self.assertRaisesRegexp(Exception, "Invalid MAC address!", set_mac, mac)
                return
            if mac_regex.match(mac) is None:
                self.assertRaisesRegexp(Exception, "Invalid MAC address!", set_mac, mac)
                return
            if int(parts[0], base=16) & 1:
                self.assertRaisesRegexp(Exception, "Multicast-Flag ", set_mac, mac)
                return
            nd.mac = mac

        # Try some bad macs
        test_mac("ff:ff:ff:ff:ff")
        test_mac("ff:ff:ff:ff:ff:ff")
        test_mac("ff:asjfjsdaf:ff:ff:ff:ff")
        test_mac("aj:00:ff:1f:ff:ff")
        test_mac("ff:ff:ff:ff:ff:ff:ff")

        # Assert that we have no mac assigned
        session.session.add(nd)
        self.assertRaises(IntegrityError, session.session.commit)
        session.session.rollback()

        # Assert a correct mac
        test_mac("00:00:00:00:00:00")

        # Assert that we have the mac assigned
        session.session.add(nd)
        session.session.commit()

        # Wipe the instance
        session.session.delete(nd)
        session.session.commit()


class Test_020_NetworkDeviceMethods(FixtureDataTestBase):
    datasets = [DormitoryData, VLANData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    # placeholder because the set_v4 method is gone
    pass


class Test_030_IpModel(FixtureDataTestBase):
    datasets = [DormitoryData, VLANData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    def tearDown(self):
        host.Ip.q.delete()
        session.session.commit()
        super(Test_030_IpModel, self).tearDown()

    def test_0010_is_ip_valid(self):
        ip_addr = host.Ip()
        self.assertFalse(ip_addr.is_ip_valid)

    def test_0020_change_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = host.Ip(net_device=netdev, address=ip, subnet=subnet)

        session.session.add(ip_addr)
        session.session.commit()

        ip_addr = host.Ip.q.first()
        self.assertEqual(ip_addr.address, ip)

        ip = get_free_ip((subnet,))
        ip_addr.change_ip(ip, subnet)
        session.session.commit()

        ip_addr = host.Ip.q.first()
        self.assertEqual(ip_addr.address, ip)

        host.Ip.q.delete()
        session.session.commit()

    def test_0030_delete_address(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = host.Ip(net_device=netdev, address=ip, subnet=subnet)

        session.session.add(ip_addr)
        session.session.commit()

        ip_addr.address = None
        self.assertIsNone(ip_addr.address)

        self.assertRaisesInTransaction(IntegrityError, session.session.commit)

    def test_0040_delete_subnet(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = host.Ip(net_device=netdev, address=ip, subnet=subnet)

        session.session.add(ip_addr)
        session.session.commit()

        ip_addr.subnet = None
        self.assertIsNone(ip_addr.subnet)

        self.assertRaisesInTransaction(IntegrityError, session.session.commit)


class Test_040_IpEvents(FixtureDataTestBase):
    datasets = [DormitoryData, VLANData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    def test_0010_correct_subnet_and_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()

        ip = get_free_ip((subnet, ))

        ip_addr = host.Ip(net_device=netdev)
        ip_addr.address = ip
        ip_addr.subnet = subnet
        session.session.add(ip_addr)
        session.session.commit()

        netdev = host.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = host.Ip(address=ip, subnet=subnet, net_device=netdev)
        session.session.add(ip_addr)
        session.session.commit()

        host.Ip.q.filter(host.Ip.net_device == netdev).delete()
        session.session.commit()


    def test_0020_missing_subnet(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()

        ip = get_free_ip((subnet, ))
        ip_addr = host.Ip(net_device=netdev)
        ip_addr.address = ip

        def commit():
            session.session.add(ip_addr)
            session.session.commit()
        self.assertRaises(IntegrityError, commit)

    def test_0030_missing_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()

        ip_addr = host.Ip(net_device=netdev)
        ip_addr.subnet = subnet

        def commit():
            session.session.add(ip_addr)
            session.session.commit()
        self.assertRaises(IntegrityError, commit)

    def test_0040_wrong_subnet(self):
        subnets = dormitory.Subnet.q.all()
        netdev = host.NetDevice.q.first()
        ip = get_free_ip((subnets[0], ))

        ip_addr = host.Ip(net_device=netdev, address=ip)

        def assign_subnet():
            ip_addr.subnet = subnets[1]

        self.assertRaisesRegexp(AssertionError, "Given subnet does not contain the ip", assign_subnet)

        ip_addr = host.Ip(net_device=netdev, subnet=subnets[1])

        def assign_ip():
            ip_addr.address = ip

        self.assertRaisesRegexp(AssertionError, "Subnet does not contain the given ip", assign_ip)

        def new_instance():
            host.Ip(net_device=netdev, subnet=subnets[1], address=ip)

        self.assertRaisesRegexp(AssertionError, "Subnet does not contain the given ip", new_instance)


class Test_060_Cascades(FixtureDataTestBase):
    datasets = [DormitoryData, VLANData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData, IpData, TrafficVolumeData]

    def test_0010_cascade_on_delete_ip(self):
        test_ip = host.Ip.q.filter_by(address=IpData.dummy_ip.address).one()
        session.session.delete(test_ip)
        session.session.commit()
        self.assertIsNone(accounting.TrafficVolume.q.first())

    def test_0010_cascade_on_delete_netdevice(self):
        test_net_device = host.NetDevice.q.filter_by(
            mac=UserNetDeviceData.dummy_device.mac).one()
        session.session.delete(test_net_device)
        session.session.commit()
        self.assertIsNone(host.Ip.q.first())
        self.assertIsNone(accounting.TrafficVolume.q.first())

    def test_0010_cascade_on_delete_host(self):
        test_host = host.UserHost.q.first()
        session.session.delete(test_host)
        session.session.commit()
        self.assertIsNone(host.NetDevice.q.first())
        self.assertIsNone(host.Ip.q.first())
        self.assertIsNone(accounting.TrafficVolume.q.first())

    def test_0010_cascade_on_delete_user(self):
        test_user = user.User.q.filter_by(login=UserData.dummy_user.login).one()
        session.session.delete(test_user)
        session.session.commit()
        self.assertIsNone(host.Host.q.first())
        self.assertIsNone(host.NetDevice.q.first())
        self.assertIsNone(host.Ip.q.first())
        self.assertIsNone(accounting.TrafficVolume.q.first())
