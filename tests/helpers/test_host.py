# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import unittest
from random import randint

import ipaddr

from pycroft.helpers.net import sort_ports
from pycroft.lib.host import change_mac, generate_hostname
from pycroft.lib.net import SubnetFullException, get_free_ip
from pycroft.model.host import IP
from tests import FactoryDataTestBase, factories


class TestSimpleHostsHelper(unittest.TestCase):
    def test_sort_ports(self):
        ports = [f"{let}{num}" for let in "ABCDEFG" for num in range(1, 24)]

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

    def test_generate_hostname(self):
        ips = [(141, 30, 228, 10), (10, 10, 10, 1)]
        for ip in ips:
            byte1, byte2, byte3, byte4 = ip
            expected = u"x{:02x}{:02x}{:02x}{:02x}".format(byte1, byte2, byte3, byte4)
            generated = generate_hostname(
                ipaddr.IPv4Address("{:d}.{:d}.{:d}.{:d}".format(byte1, byte2, byte3, byte4)))
            self.assertEqual(generated, expected)


class TestIpHelper(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.subnets = factories.SubnetFactory.create_batch(10)
        self.host = factories.HostFactory()

    @staticmethod
    def calculate_usable_ips(net):
        ips = ipaddr.IPNetwork(net.address).numhosts
        reserved = net.reserved_addresses_bottom + net.reserved_addresses_top
        return ips - reserved - 2

    def test_get_free_ip_simple(self):
        for subnet in self.subnets:
            ip, subnet = get_free_ip((subnet,))
            self.assertIn(ip, subnet.address)

    def fill_net(self, net, interface):
        for num in range(0, self.calculate_usable_ips(net)):
            ip, _ = get_free_ip((net,))
            self.session.add(IP(address=ip, subnet=net, interface=interface))
        self.session.commit()

    def test_get_free_ip_next_to_full(self):
        first_net = self.subnets[0]
        second_net = self.subnets[1]
        subnets = (first_net, second_net)
        host = self.host

        interface = host.interfaces[0]
        self.fill_net(first_net, interface)
        self.session.refresh(first_net)
        self.assertRaises(SubnetFullException, get_free_ip, (first_net,))
        try:
            get_free_ip(subnets)
        except SubnetFullException:
            self.fail("Subnets should have free IPs.")
        self.fill_net(subnets[1], interface)
        self.assertRaises(SubnetFullException, get_free_ip, subnets)

        self.session.delete(host)
        self.session.commit()


# TODO this is actually a lib test
class TestChangeMacInterface(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.processing_user = factories.UserFactory()
        self.interface = factories.InterfaceFactory()

    def test_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        change_mac(self.interface, new_mac, self.processing_user)
        self.assertEqual(self.interface.mac, new_mac)
