# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re

from tests import OldPythonTestCase, FixtureDataTestBase
from pycroft import model
from pycroft.model import session, hosts, dormitory, user, accounting

from tests.model.fixtures.hosts_fixtures import DormitoryData, VLanData, \
    SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData, IpData, \
    TrafficVolumeData
from pycroft.helpers.host_helper import get_free_ip


class Test_010_NetDeviceValidators(OldPythonTestCase):
    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()
        cls.host = hosts.UserHost(user_id = 1)
        session.session.commit()

    def test_0010_mac_validate(self):
        mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")

        nd = hosts.UserNetDevice(host=self.host)
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
        self.assertRaisesRegexp(Exception, "\(IntegrityError\) netdevice.mac may not be NULL", session.session.commit)
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
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    # placeholder because the set_v4 method is gone
    pass


class Test_030_IpModel(FixtureDataTestBase):
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    def tearDown(self):
        session.session.remove()
        hosts.Ip.q.delete()
        session.session.commit()
        super(Test_030_IpModel, self).tearDown()

    def test_0010_is_ip_valid(self):
        ip_addr = hosts.Ip()
        self.assertFalse(ip_addr.is_ip_valid)

    def test_0020_change_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = hosts.Ip(net_device=netdev, address=ip, subnet=subnet)

        session.session.add(ip_addr)
        session.session.commit()

        ip_addr = hosts.Ip.q.first()
        self.assertEqual(ip_addr.address, ip)

        ip = get_free_ip((subnet,))
        ip_addr.change_ip(ip, subnet)
        session.session.commit()

        ip_addr = hosts.Ip.q.first()
        self.assertEqual(ip_addr.address, ip)

        hosts.Ip.q.delete()
        session.session.commit()

    def test_0030_delete_address(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = hosts.Ip(net_device=netdev, address=ip, subnet=subnet)

        session.session.add(ip_addr)
        session.session.commit()

        ip_addr.address = None
        self.assertIsNone(ip_addr.address)

        self.assertRaisesRegexp(Exception, r"\(IntegrityError\) ip.address may not be NULL.*", session.session.commit)

    def test_0040_delete_subnet(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = hosts.Ip(net_device=netdev, address=ip, subnet=subnet)

        session.session.add(ip_addr)
        session.session.commit()

        ip_addr.subnet = None
        self.assertIsNone(ip_addr.subnet)

        self.assertRaisesRegexp(Exception, r"\(IntegrityError\) ip.subnet_id may not be NULL.*", session.session.commit)


class Test_040_IpEvents(FixtureDataTestBase):
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    def test_0010_correct_subnet_and_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()

        ip = get_free_ip((subnet, ))

        ip_addr = hosts.Ip(net_device=netdev)
        ip_addr.address = ip
        ip_addr.subnet = subnet
        session.session.add(ip_addr)
        session.session.commit()

        netdev = hosts.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = hosts.Ip(address=ip, subnet=subnet, net_device=netdev)
        session.session.add(ip_addr)
        session.session.commit()

        hosts.Ip.q.filter(hosts.Ip.net_device == netdev).delete()
        session.session.commit()


    def test_0020_missing_subnet(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()

        ip = get_free_ip((subnet, ))
        ip_addr = hosts.Ip(net_device=netdev)
        ip_addr.address = ip

        def commit():
            session.session.add(ip_addr)
            session.session.commit()
        self.assertRaisesRegexp(Exception, r"\(IntegrityError\) ip.subnet_id may not be NULL .*", commit)

    def test_0030_missing_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()

        ip_addr = hosts.Ip(net_device=netdev)
        ip_addr.subnet = subnet

        def commit():
            session.session.add(ip_addr)
            session.session.commit()
        self.assertRaisesRegexp(Exception, r"\(IntegrityError\) ip.address may not be NULL .*", commit)

    def test_0040_wrong_subnet(self):
        subnets = dormitory.Subnet.q.all()
        netdev = hosts.NetDevice.q.first()
        ip = get_free_ip((subnets[0], ))

        ip_addr = hosts.Ip(net_device=netdev, address=ip)

        def assign_subnet():
            ip_addr.subnet = subnets[1]

        self.assertRaisesRegexp(AssertionError, "Given subnet does not contain the ip", assign_subnet)

        ip_addr = hosts.Ip(net_device=netdev, subnet=subnets[1])

        def assign_ip():
            ip_addr.address = ip

        self.assertRaisesRegexp(AssertionError, "Subnet does not contain the given ip", assign_ip)

        def new_instance():
            hosts.Ip(net_device=netdev, subnet=subnets[1], address=ip)

        self.assertRaisesRegexp(AssertionError, "Subnet does not contain the given ip", new_instance)


class Test_050_SwitchEvents(FixtureDataTestBase):
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    def tearDown(self):
        session.session.remove()
        hosts.Ip.q.delete()

        # Delete all derived NetDevices
        for switch_dev in hosts.SwitchNetDevice.q.all():
            session.session.delete(switch_dev)
        for user_dev in hosts.UserNetDevice.q.all():
            session.session.delete(user_dev)
        for server_dev in hosts.ServerNetDevice.q.all():
            session.session.delete(server_dev)

        for switch in hosts.Switch.q.all():
            session.session.delete(switch)

        session.session.commit()
        super(Test_050_SwitchEvents, self).tearDown()

    def setUp(self):
        super(Test_050_SwitchEvents, self).setUp()
        self.subnet = dormitory.Subnet.q.first()
        self.user = user.User.q.first()
        self.room = dormitory.Room.q.first()

    def make_switch(self, **kwargs):
        if "name" not in kwargs:
            kwargs["name"] = "testswitch1"

        new_switch = hosts.Switch(room=self.room, user=self.user, **kwargs)
        return new_switch

    def make_ip(self, num, net_dev):
        net_parts = self.subnet.gateway.split(".")
        net_parts[3] = str(1 + self.subnet.reserved_addresses + num)
        ip_addr = '.'.join(net_parts)

        return hosts.Ip(net_device=net_dev, address=ip_addr, subnet=self.subnet)

    def test_0010_check_missing_management_ip_no_ips(self):
        new_switch = self.make_switch()
        session.session.add(new_switch)
        self.assertRaisesRegexp(AssertionError, "A management ip has to be set", session.session.commit)

    def test_0020_check_missing_management_ip_have_one_ip(self):
        new_switch = self.make_switch()

        netdev = hosts.SwitchNetDevice(mac="00:00:00:00:00:00", host=new_switch)
        ip = self.make_ip(1, netdev)

        session.session.add(new_switch)
        session.session.add(ip)
        self.assertRaisesRegexp(AssertionError, "A management ip has to be set", session.session.commit)

    def test_0030_check_missing_management_ip_have_ips(self):
        new_switch = self.make_switch()

        netdev = hosts.SwitchNetDevice(mac="00:00:00:00:00:00", host=new_switch)
        ips = []
        for num in range(1, 3):
            ip = self.make_ip(num, netdev)
            ips.append(ip)

        session.session.add(new_switch)
        session.session.add_all(ips)
        self.assertRaisesRegexp(AssertionError, "A management ip has to be set", session.session.commit)


    def test_0040_check_wrong_management_ip_no_ips(self):
        dflt_netdev = hosts.NetDevice.q.first()
        ip = self.make_ip(1, dflt_netdev)
        session.session.add(ip)

        new_switch = self.make_switch()
        new_switch.management_ip = ip

        session.session.add(new_switch)
        self.assertRaisesRegexp(AssertionError, "the management ip is not valid on this switch", session.session.commit)

    def test_0050_check_wrong_management_ip_one_ip(self):
        dflt_netdev = hosts.NetDevice.q.first()
        ip = self.make_ip(1, dflt_netdev)
        session.session.add(ip)

        new_switch = self.make_switch()
        new_switch.management_ip = ip

        netdev = hosts.SwitchNetDevice(mac="00:00:00:00:00:00", host=new_switch)
        ip = self.make_ip(2, netdev)

        session.session.add(new_switch)
        session.session.add(ip)
        self.assertRaisesRegexp(AssertionError, "the management ip is not valid on this switch", session.session.commit)

    def test_0060_check_wrong_management_ip_have_ips(self):
        dflt_netdev = hosts.NetDevice.q.first()
        ip = self.make_ip(1, dflt_netdev)
        session.session.add(ip)

        new_switch = self.make_switch()
        new_switch.management_ip = ip

        netdev = hosts.SwitchNetDevice(mac="00:00:00:00:00:00", host=new_switch)
        ips = []
        for num in range(3, 5):
            ip = self.make_ip(num, netdev)
            ips.append(ip)

        session.session.add(new_switch)
        session.session.add_all(ips)
        self.assertRaisesRegexp(AssertionError, "the management ip is not valid on this switch", session.session.commit)

    def test_0070_check_correct_management_ip_have_one_ip(self):
        new_switch = self.make_switch()

        netdev = hosts.SwitchNetDevice(mac="00:00:00:00:00:00", host=new_switch)
        ip = self.make_ip(1, netdev)
        new_switch.management_ip = ip

        session.session.add(new_switch)
        session.session.add(netdev)
        session.session.add(ip)
        session.session.commit()

    def test_0080_check_correct_management_ip_have_ips(self):
        new_switch = self.make_switch()

        netdev = hosts.SwitchNetDevice(mac="00:00:00:00:00:00", host=new_switch)

        ips = []

        for num in range(3, 5):
            ip = self.make_ip(num, netdev)
            ips.append(ip)

        new_switch.management_ip = ips[0]

        session.session.add(new_switch)
        session.session.add(netdev)
        session.session.add_all(ips)
        session.session.commit()


class Test_060_Cascades(FixtureDataTestBase):
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData, IpData, TrafficVolumeData]

    def test_0010_cascade_on_delete_ip(self):
        session.session.delete(hosts.Ip.q.get(1))
        session.session.commit()
        self._assertIsNone(accounting.TrafficVolume.q.first())

    def test_0010_cascade_on_delete_netdevice(self):
        session.session.delete(hosts.NetDevice.q.get(1))
        session.session.commit()
        self._assertIsNone(hosts.Ip.q.first())
        self._assertIsNone(accounting.TrafficVolume.q.first())

    def test_0010_cascade_on_delete_host(self):
        session.session.delete(hosts.Host.q.get(1))
        session.session.commit()
        self._assertIsNone(hosts.NetDevice.q.first())
        self._assertIsNone(hosts.Ip.q.first())
        self._assertIsNone(accounting.TrafficVolume.q.first())

    def test_0010_cascade_on_delete_user(self):
        session.session.delete(user.User.q.get(1))
        session.session.commit()
        self._assertIsNone(hosts.Host.q.first())
        self._assertIsNone(hosts.NetDevice.q.first())
        self._assertIsNone(hosts.Ip.q.first())
        self._assertIsNone(accounting.TrafficVolume.q.first())
