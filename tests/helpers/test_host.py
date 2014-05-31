import unittest
from tests import FixtureDataTestBase
from random import randint
import ipaddr

from pycroft.lib.host import change_mac

from pycroft.helpers.host import sort_ports, generate_hostname, \
    get_free_ip, select_subnet_for_ip, SubnetFullException
from pycroft.model import dormitory, session, user, logging
from pycroft.model.host import Host, UserNetDevice, Ip

from tests.helpers.fixtures.host_fixtures import DormitoryData, VLANData, \
    SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData


class Test_010_SimpleHostsHelper(unittest.TestCase):
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


class Test_020_IpHelper(FixtureDataTestBase):
    datasets = [DormitoryData, VLANData, SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData]

    def ip_s1(self, num):
        net_parts = SubnetData.subnet1.gateway.split(".")
        net_parts[3] = str(1 + SubnetData.subnet1.reserved_addresses + num)
        return '.'.join(net_parts)

    def ip_s2(self, num):
        net_parts = SubnetData.subnet2.gateway.split(".")
        net_parts[3] = str(1 + SubnetData.subnet2.reserved_addresses + num)
        return '.'.join(net_parts)

    def _number_of_ips_in(self, net):
        total_hosts = ipaddr.IPNetwork(net.address).numhosts
        return (total_hosts
                - net.reserved_addresses
                - 2                      # network & broadcast addresses
                )

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
        host = Host.q.filter(Host.id == UserHostData.dummy_host1.id).one()

        self.assertEqual(len(subnets), 2)
        total_ips = sum([self._number_of_ips_in(net) for net in subnets])
        first_net_ips = self._number_of_ips_in(subnets[0])

        nd = UserNetDevice(mac="00:00:00:00:00:00", host = host)
        for num in range(0, total_ips + 2):
            if num >= total_ips:
                self.assertRaises(SubnetFullException, get_free_ip, subnets)
                continue
            ip = get_free_ip(subnets)
            net = select_subnet_for_ip(ip, subnets)
            if num < first_net_ips:
                self.assertEqual(ip, self.ip_s1(num))
            else:
                self.assertEqual(ip, self.ip_s2(num % first_net_ips))

            ip_addr = Ip(address=ip, subnet=net, net_device=nd)
            session.session.add(ip_addr)
            session.session.commit()

        Ip.q.filter(Ip.net_device == nd).delete()
        session.session.delete(nd)
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



