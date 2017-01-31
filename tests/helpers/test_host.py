# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from itertools import islice
from random import randint

import ipaddr

from tests import FixtureDataTestBase
from pycroft.lib.host import change_mac, generate_hostname
from pycroft.helpers.net import sort_ports
from pycroft.lib.net import SubnetFullException, get_free_ip
from pycroft.model import session, user, logging
from pycroft.model.host import UserInterface, PublicIP, HostReservation
from pycroft.model.net import GlobalSubnet
from tests.fixtures.dummy.facilities import BuildingData, RoomData
from tests.fixtures.dummy.host import (
    UserHostData, UserInterfaceData)
from tests.fixtures.dummy.net import SubnetData, VLANData
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
        ips = [(141, 30, 228, 10), (10, 10, 10, 1)]
        for ip in ips:
            byte1, byte2, byte3, byte4 = ip
            expected = u"x{:02x}{:02x}{:02x}{:02x}".format(byte1, byte2, byte3, byte4)
            generated = generate_hostname(
                ipaddr.IPv4Address("{:d}.{:d}.{:d}.{:d}".format(byte1, byte2, byte3, byte4)))
            self.assertEqual(generated, expected)


class Test_020_IpHelper(FixtureDataTestBase):
    datasets = [BuildingData, VLANData, SubnetData, RoomData, UserData,
                UserHostData, UserInterfaceData]

    def calculate_usable_ips(self, net):
        ips = ipaddr.IPNetwork(net.address).numhosts
        return ips - net.reserved_addresses - 2

    def test_0010_get_free_ip_simple(self):
        subnets = GlobalSubnet.q.all()
        for subnet in subnets:
            ip, subnet = get_free_ip((subnet,))
            self.assertIn(ip, subnet.address)

    def fill_net(self, net, interface):
        for num in range(0, self.calculate_usable_ips(net)):
            ip, _ = get_free_ip((net,))
            session.session.add(PublicIP(address=ip, subnet=net,
                                         interface=interface))
        session.session.commit()

    def test_0030_get_free_ip_next_to_full(self):
        first_net = GlobalSubnet.q.filter_by(
            address=SubnetData.user_ipv4.address).one()
        second_net = GlobalSubnet.q.filter_by(
            address=SubnetData.dummy_subnet2.address).one()
        subnets = (first_net, second_net)
        host = HostReservation.q.one()

        interface = host.user_interfaces[0]
        self.fill_net(first_net, interface)
        session.session.refresh(first_net)
        self.assertRaises(SubnetFullException, get_free_ip, (first_net,))
        try:
            get_free_ip(subnets)
        except SubnetFullException:
            self.fail("Subnets should have free IPs.")
        self.fill_net(subnets[1], interface)
        self.assertRaises(SubnetFullException, get_free_ip, subnets)

        session.session.delete(host)
        session.session.commit()


class Test_030_change_mac_interface(FixtureDataTestBase):
    datasets = [UserInterfaceData, UserData]

    def setUp(self):
        super(Test_030_change_mac_interface, self).setUp()
        self.processing_user = user.User.q.filter_by(
            login=UserData.dummy.login).one()
        self.interface = UserInterface.q.filter_by(
            mac=UserInterfaceData.dummy.mac).one()

    def test_0010_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        change_mac(self.interface, new_mac, self.processing_user)
        self.assertEqual(self.interface.mac, new_mac)
