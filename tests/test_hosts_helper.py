# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime
from fixture import DataSet
from tests import OldPythonTestCase, FixtureDataTestBase
from random import randint
import ipaddr

from pycroft.helpers.host_helper import sort_ports, generate_hostname, get_free_ip, select_subnet_for_ip, SubnetFullException
from pycroft.model import dormitory, hosts, session


class DormitoryData(DataSet):
    class dummy_house:
        number = "01"
        short_name = "abc"
        street = "dummy"


class VLanData(DataSet):
    class vlan1:
        name = "vlan1"
        tag = "1"
    class vlan2:
        name = "vlan2"
        tag = 2


class SubnetData(DataSet):
    class subnet1:
        address = "141.30.216.0/24"
        gateway = "141.30.216.1"
        dns_domain = "wh12.tu-dresden.de"
        reserved_addresses = 10
    class subnet2:
        address = "141.30.227.0/24"
        gateway = "141.30.227.1"
        dns_domain = "wh13.tu-dresden.de"
        reserved_addresses = 10


class RoomData(DataSet):
    class dummy_room:
        number = 1
        level = 1
        inhabitable = True
        dormitory = DormitoryData.dummy_house


class UserData(DataSet):
    class dummy_user:
        login = "test"
        name = "John Doe"
        registration_date = datetime.now()
        room = RoomData.dummy_room


class HostData(DataSet):
    class dummy_host1:
        hostname = "host1"
        user = UserData.dummy_user
        room = RoomData.dummy_room
    class dummy_host2:
        hostname = "host2"
        user = UserData.dummy_user
        room = RoomData.dummy_room


class NetDeviceData(DataSet):
    class dummy_device:
        mac = "00:00:00:00:00:00"
        host = HostData.dummy_host1


class Test_010_SimpleHostsHelper(OldPythonTestCase):
    def test_0010_sort_ports(self):
        ports = []
        for letter in ["A", "B", "C", "D", "E", "F", "G"]:
            for number in range(1, 24):
                ports.append("%s%d" % (letter, number))

        class fake_port(object):
            def __init__(self, name):
                self.name = name

        pool = list(ports)
        shuffled = []
        for selected in range(0, len(ports)):
            idx = randint(0, len(pool) - 1)
            shuffled.append(fake_port(pool[idx]))
            del pool[idx]
        resorted = [p.name for p in sort_ports(shuffled)]
        self.assertEqual(resorted, ports)

    def test_0020_generate_hostname(self):
        networks = ["141.30.228", "10.10.10", "141.30.126"]
        for hostpart in range(1, 255):
            for net in networks:
                expected = "whdd%d" % hostpart
                generated = generate_hostname("%s.%d" % (net, hostpart))
                self.assertEqual(generated, expected)


class Test_030_IpHelper(FixtureDataTestBase):
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, HostData, NetDeviceData]

    def ip_s1(self, num):
        net_parts = SubnetData.subnet1.gateway.split(".")
        net_parts[3] = str(1 + SubnetData.subnet1.reserved_addresses + num)
        return '.'.join(net_parts)

    def ip_s2(self, num):
        net_parts = SubnetData.subnet2.gateway.split(".")
        net_parts[3] = str(1 + SubnetData.subnet2.reserved_addresses + num)
        return '.'.join(net_parts)

    def test_0010_get_free_ip_simple(self):
        subnets = dormitory.Subnet.q.order_by(dormitory.Subnet.gateway).all()
        ip = get_free_ip(subnets)
        self.assertEqual(ip, self.ip_s1(0))

    def test_0020_select_subnet_for_ip(self):
        subnets = dormitory.Subnet.q.order_by(dormitory.Subnet.gateway).all()
        for subnet in subnets:
            for ip in ipaddr.IPNetwork(subnet.address).iterhosts():
                selected = select_subnet_for_ip(ip.compressed, subnets)
                self.assertEqual(subnet, selected)

    def test_0030_get_free_ip_next_to_full(self):
        subnets = dormitory.Subnet.q.order_by(dormitory.Subnet.gateway).all()
        host = hosts.Host.q.filter(hosts.Host.hostname == HostData.dummy_host2.hostname).one()

        for num in range(0, 490):
            if num >= 488:
                self.assertRaises(SubnetFullException, get_free_ip, subnets)
                continue
            ip = get_free_ip(subnets)
            net = select_subnet_for_ip(ip, subnets)
            if num < 244:
                self.assertEqual(ip, self.ip_s1(num))
            else:
                self.assertEqual(ip, self.ip_s2(num % 244))
            nd = hosts.NetDevice(host=host, mac="00:00:00:00:00:00", ipv4=ip, subnet=net)
            session.session.add(nd)
            session.session.commit()

        hosts.NetDevice.q.filter(hosts.NetDevice.host==host).delete()
        session.session.commit()

