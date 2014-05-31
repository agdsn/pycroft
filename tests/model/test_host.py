import re
import unittest

from tests import FixtureDataTestBase
from pycroft import model
from pycroft.model import session, host, dormitory, user, accounting

from tests.model.fixtures.host_fixtures import DormitoryData, VLANData, \
    SubnetData, RoomData, UserData, UserHostData, UserNetDeviceData, IpData, \
    TrafficVolumeData
from pycroft.helpers.host import get_free_ip, MacExistsException
from tests import REGEX_NOT_NULL_CONSTRAINT


class Test_010_NetDeviceValidators(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()
        cls.host = host.UserHost(user_id = 1)
        session.session.commit()

    def test_0010_mac_validate(self):
        mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")

        nd = host.UserNetDevice(host=self.host)
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
                self.assertRaisesRegexp(Exception, "Multicast flag ", set_mac, mac)
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
        self.assertRaisesRegexp(Exception, REGEX_NOT_NULL_CONSTRAINT, session.session.commit)
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
        session.session.remove()
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

        self.assertRaisesRegexp(Exception, REGEX_NOT_NULL_CONSTRAINT, session.session.commit)

    def test_0040_delete_subnet(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        ip_addr = host.Ip(net_device=netdev, address=ip, subnet=subnet)

        session.session.add(ip_addr)
        session.session.commit()

        ip_addr.subnet = None
        self.assertIsNone(ip_addr.subnet)

        self.assertRaisesRegexp(Exception, REGEX_NOT_NULL_CONSTRAINT, session.session.commit)


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
        self.assertRaisesRegexp(Exception, REGEX_NOT_NULL_CONSTRAINT, commit)

    def test_0030_missing_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = host.NetDevice.q.first()

        ip_addr = host.Ip(net_device=netdev)
        ip_addr.subnet = subnet

        def commit():
            session.session.add(ip_addr)
            session.session.commit()
        self.assertRaisesRegexp(Exception, REGEX_NOT_NULL_CONSTRAINT, commit)

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
        session.session.delete(host.Ip.q.get(1))
        session.session.commit()
        self.assertIsNone(accounting.TrafficVolume.q.first())

    def test_0020_cascade_on_delete_net_device(self):
        session.session.delete(host.NetDevice.q.get(1))
        session.session.commit()
        self.assertIsNone(host.Ip.q.first())
        self.assertIsNone(accounting.TrafficVolume.q.first())

    def test_0030_cascade_on_delete_host(self):
        session.session.delete(host.Host.q.get(1))
        session.session.commit()
        self.assertIsNone(host.NetDevice.q.first())
        self.assertIsNone(host.Ip.q.first())
        self.assertIsNone(accounting.TrafficVolume.q.first())

    def test_0040_cascade_on_delete_user(self):
        session.session.delete(user.User.q.get(1))
        session.session.commit()
        self.assertIsNone(host.Host.q.first())
        self.assertIsNone(host.NetDevice.q.first())
        self.assertIsNone(host.Ip.q.first())
        self.assertIsNone(accounting.TrafficVolume.q.first())


class Test_070_DuplicateMACAdresses(FixtureDataTestBase):
    datasets = [VLANData, SubnetData, RoomData, UserData, UserHostData,
                UserNetDeviceData, IpData]

    def setUp(self):
        super(Test_070_DuplicateMACAdresses, self).setUp()
        self.uh = host.UserHost(user_id=1)
        self.nd = host.UserNetDevice(host=self.uh,
                                     mac="00:00:00:00:00:01")
        self.ip = host.Ip(address="141.30.216.3",
                     subnet=dormitory.Subnet.q.first(),
                     net_device=self.nd)
        session.session.add(self.nd)
        session.session.add(self.ip)
        session.session.commit()

    def tearDown(self):
        session.session.rollback()
        session.session.delete(self.nd)
        session.session.commit()
        super(Test_070_DuplicateMACAdresses, self).tearDown()

    def test_0010_duplicate_mac_on_mac_change(self):
        with self.assertRaisesRegexp(MacExistsException, "Mac already exists in this subnet!"):
            self.nd.mac = "00:00:00:00:00:00"
            session.session.add(self.nd)
            session.session.commit()

    def _add_second_host(self):
        uh = host.UserHost(user_id=2)
        nd = host.UserNetDevice(host=uh,
                                mac="00:00:00:00:00:01")
        ip = host.Ip(address="141.30.227.2",
                     subnet=dormitory.Subnet.q.get(2),
                     net_device=nd)
        session.session.add(nd)
        session.session.add(ip)
        session.session.commit()

        return (uh, nd, ip)

    def test_0020_duplicate_mac_on_ip_change(self):
        (_, _, ip) = self._add_second_host()
        with self.assertRaisesRegexp(MacExistsException, "Duplicate MAC"):
            ip.change_ip(ip="141.30.216.4",
                         subnet=dormitory.Subnet.q.first())
            session.session.commit()

    def test_0030_duplicate_mac_on_ip_insert(self):
        (uh, nd, _) = self._add_second_host()

        with self.assertRaisesRegexp(MacExistsException, "Mac already exists in this subnet!"):
            ip = host.Ip(address="141.30.227.4",
                         subnet=dormitory.Subnet.q.get(2),
                         net_device=self.nd)
            session.session.add(ip)
            session.session.commit()

    def test_0040_multiple_ips_on_same_net_device(self):
        ip = host.Ip(address="141.30.216.4",
                     subnet=dormitory.Subnet.q.first(),
                     net_device=self.nd)
        session.session.add(ip)
        session.session.commit()

        session.session.delete(ip)
        session.session.commit()

    def test_0050_bug434_other_subnets_for_mac(self):
        "regression test for #434"
        (uh, nd, _) = self._add_second_host()

        subnets = [sn.address
                   for sn in host._other_subnets_for_mac(self.nd)]
        for ip in self.nd.ips:
            self.assertNotIn(ip.subnet.address, subnets)
