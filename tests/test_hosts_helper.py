from tests import OldPythonTestCase, FixtureDataTestBase
from random import randint
import ipaddr

from pycroft.helpers.host_helper import sort_ports, generate_hostname, get_free_ip, select_subnet_for_ip, SubnetFullException
from pycroft.model import dormitory, hosts, session

from tests.fixtures.hosts_fixtures import DormitoryData, VLanData, SubnetData, RoomData, UserData, HostData, NetDeviceData


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


class Test_020_IpHelper(FixtureDataTestBase):
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
        host = hosts.Host.q.filter(hosts.Host.id == HostData.dummy_host2.id).one()

        nd = hosts.NetDevice(host=host, mac="00:00:00:00:00:00")
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

            ip_addr = hosts.Ip(address=ip, subnet=net, net_device=nd)
            session.session.add(ip_addr)
            session.session.commit()

        hosts.Ip.q.filter(hosts.Ip.net_device == nd).delete()
        hosts.NetDevice.q.filter(hosts.NetDevice.host==host).delete()
        session.session.commit()

