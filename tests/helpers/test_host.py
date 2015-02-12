# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from itertools import islice
from random import randint

import ipaddr

from tests import FixtureDataTestBase
from pycroft.lib.host import change_mac
from pycroft.helpers.host import sort_ports, generate_hostname, \
    get_free_ip, select_subnet_for_ip, SubnetFullException
from pycroft.model import facilities, session, user, logging
from pycroft.model.host import UserNetDevice, Ip, UserHost
from tests.fixtures.dummy.dormitory import DormitoryData, RoomData, VLANData
from tests.fixtures.dummy.host import (
    SubnetData, UserHostData, UserNetDeviceData)
from tests.fixtures.dummy.user import UserData


class Test_010_SimpleHostsHelper(unittest.TestCase):
    def test_0010_sort_ports(self):
        ports = ["{0}{1:d}".format(letter, number)
                 for letter in ["A", "B", "C", "D", "E", "F", "G"]
                 for number in range(1, 24)]

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
                expected = "whdd{:d}".format(hostpart)
                generated = generate_hostname("{}.{:d}".format(net, hostpart))
                self.assertEqual(generated, expected)


class Test_020_IpHelper(FixtureDataTestBase):
    datasets = [DormitoryData, VLANData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    def calculate_usable_ips(self, net):
        ips = ipaddr.IPNetwork(net.address).numhosts
        return ips - net.reserved_addresses - 2

    def assertIPInSubnet(self, ip, subnet):
        self.assertIn(ipaddr.IPAddress(ip), ipaddr.IPNetwork(subnet.address))

    def test_0010_get_free_ip_simple(self):
        subnets = facilities.Subnet.q.order_by(facilities.Subnet.gateway).all()
        for subnet in subnets:
            ip = get_free_ip((subnet,))
            self.assertIPInSubnet(ip, subnet)

    def test_0020_select_subnet_for_ip(self):
        subnets = facilities.Subnet.q.order_by(facilities.Subnet.gateway).all()
        for subnet in subnets:
            for ip in islice(ipaddr.IPNetwork(subnet.address).iterhosts(), 100):
                selected = select_subnet_for_ip(ip.compressed, subnets)
                self.assertEqual(subnet, selected)

    def fill_net(self, net, net_device):
        for num in range(0, self.calculate_usable_ips(net)):
            ip = get_free_ip((net,))
            session.session.add(Ip(address=ip, subnet=net, net_device=net_device))
        session.session.commit()

    def test_0030_get_free_ip_next_to_full(self):
        subnets = facilities.Subnet.q.filter_by(ip_type="4").limit(2).all()
        host = UserHost.q.one()

        self.assertEqual(len(subnets), 2)
        total_ips = sum(self.calculate_usable_ips(net) for net in subnets)

        first_net = subnets[0]
        self.fill_net(first_net, host.user_net_device)
        session.session.refresh(first_net)
        self.assertRaises(SubnetFullException, get_free_ip, (first_net,))
        try:
            get_free_ip(subnets)
        except SubnetFullException:
            self.fail("Subnets should have free IPs.")
        self.fill_net(subnets[1], host.user_net_device)
        self.assertRaises(SubnetFullException, get_free_ip, subnets)

        session.session.delete(host)
        session.session.commit()


class Test_030_change_mac_net_device(FixtureDataTestBase):
    datasets = [UserNetDeviceData, UserData]

    def setUp(self):
        super(Test_030_change_mac_net_device, self).setUp()
        self.processing_user = user.User.q.get(1)
        self.dummy_device = UserNetDevice.q.get(1)

    def tearDown(self):
        logging.LogEntry.q.delete()
        session.session.commit()
        super(Test_030_change_mac_net_device, self).tearDown()

    def test_0010_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        change_mac(self.dummy_device, new_mac, self.processing_user)
        self.assertEqual(self.dummy_device.mac, new_mac)
