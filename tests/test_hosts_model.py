import unittest
import re

from tests import OldPythonTestCase, FixtureDataTestBase
from pycroft import model
from pycroft.model import session, hosts, dormitory

from tests.fixtures.hosts_fixtures import DormitoryData, VLanData, SubnetData, RoomData, UserData, HostData, NetDeviceData
from pycroft.helpers.host_helper import get_free_ip


class Test_010_NetDeviceValidators(OldPythonTestCase):
    @classmethod
    def setUpClass(cls):
        session.reinit_session("sqlite://")
        model.drop_db_model()
        model.create_db_model()
        cls.host = hosts.Host(hostname="dummy")
        session.session.commit()

    def test_0010_mac_validate(self):
        mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")

        nd = hosts.NetDevice(host=self.host)
        def set_mac(mac):
            nd.mac = mac

        def test_mac(mac):
            parts = mac.split(":")
            if len(mac) != 17 or len(parts) != 6:
                self.assertRaisesRegexp(Exception, "invalid MAC address!", set_mac, mac)
                return
            if mac_regex.match(mac) is None:
                self.assertRaisesRegexp(Exception, "invalid MAC address!", set_mac, mac)
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
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, HostData, NetDeviceData]

    def test_0010_set_v4address(self):
        subnets = dormitory.Subnet.q.all()
        netdev = hosts.NetDevice.q.first()

        ip = get_free_ip((subnets[0], ))
        def call_method(subnet):
            netdev.set_v4address(ip, subnet)

        call_method(subnets[0])
        self.assertRaises(AssertionError, call_method, subnets[1])


class Test_030_NetworkDeviceEvents(FixtureDataTestBase):
    datasets = [DormitoryData, VLanData, SubnetData, RoomData, UserData, HostData, NetDeviceData]

    def test_0010_correct_subnet_and_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()

        netdev.ipv4 = get_free_ip((subnet, ))
        netdev.subnet = subnet
        session.session.commit()

        netdev = hosts.NetDevice.q.first()
        ip = get_free_ip((subnet, ))
        netdev.set_v4address(ip, subnet)
        session.session.commit()


    def test_0020_missing_subnet(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()

        netdev.ipv4 = get_free_ip((subnet, ))

        def commit():
            session.session.commit()
        self.assertRaisesRegexp(AssertionError, "NetDevice has an ip bot no Subnet assigned!", commit)

    def test_0030_missing_ip(self):
        subnet = dormitory.Subnet.q.first()
        netdev = hosts.NetDevice.q.first()

        netdev.subnet = subnet

        def commit():
            session.session.commit()
        self.assertRaisesRegexp(AssertionError, "A Subnet is assigned but no ip was set", commit)

    def test_0040_wrong_subnet(self):
        subnets = dormitory.Subnet.q.all()
        netdev = hosts.NetDevice.q.first()

        netdev.ipv4 = get_free_ip((subnets[0], ))
        netdev.subnet = subnets[1]

        def commit():
            session.session.commit()
        self.assertRaisesRegexp(AssertionError, "Assigned Subnet does not contain the assigned ip", commit)