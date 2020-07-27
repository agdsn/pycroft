# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re
from itertools import chain

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from pycroft.lib.net import get_free_ip
from pycroft.model import session, host, user
from pycroft.model.net import VLAN
from pycroft.model.types import InvalidMACAddressException
from tests import FixtureDataTestBase, FactoryDataTestBase
from tests.fixtures.dummy.host import IPData, HostData, InterfaceData, \
    SwitchPortData
from tests.fixtures.dummy.net import SubnetData, VLANData
from tests.fixtures.dummy.traffic import TrafficVolumeData
from tests.fixtures.dummy.user import UserData
from .. import factories


class TestInterfaceValidators(FactoryDataTestBase):
    mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")

    def create_factories(self):
        super().create_factories()
        self.host = factories.host.HostFactory()

    def assertSetMAC(self, interface, mac):
        parts = mac.split(":")
        if len(mac) != 17 or len(parts) != 6:
            with self.assertRaises(InvalidMACAddressException):
                interface.mac = mac
            return
        if self.mac_regex.match(mac) is None:
            with self.assertRaises(InvalidMACAddressException):
                interface.mac = mac
            return
        if int(parts[0], base=16) & 1:
            with self.assertRaises(InvalidMACAddressException):
                interface.mac = mac
            return
        interface.mac = mac

    def test_mac_validation(self):
        interface = host.Interface(host=self.host)

        # Try some bad macs
        self.assertSetMAC(interface, "ff:ff:ff:ff:ff")
        self.assertSetMAC(interface, "ff:ff:ff:ff:ff:ff")
        self.assertSetMAC(interface, "ff:asjfjsdaf:ff:ff:ff:ff")
        self.assertSetMAC(interface, "aj:00:ff:1f:ff:ff")
        self.assertSetMAC(interface, "ff:ff:ff:ff:ff:ff:ff")

        # Assert that we have no mac assigned
        session.session.add(interface)
        self.assertRaises(IntegrityError, session.session.commit)
        session.session.rollback()

        # Assert a correct mac
        self.assertSetMAC(interface, "00:00:00:01:00:00")

        # Assert that we have the mac assigned
        session.session.add(interface)
        session.session.commit()

        # Wipe the instance
        session.session.delete(interface)
        session.session.commit()

class IpModelTestBase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.subnets = factories.net.SubnetFactory.create_batch(5)
        self.subnet = self.subnets[0]
        self.interface = factories.host.InterfaceFactory()

    def pick_ip(self):
        ip, _ = get_free_ip((self.subnet,))
        addr = host.IP(interface=self.interface, address=ip, subnet=self.subnet)
        session.session.add(addr)
        session.session.commit()
        return addr


class TestIpModel(IpModelTestBase):
    def test_0030_delete_address(self):
        ip_addr = self.pick_ip()

        with self.assertRaises(IntegrityError):
            ip_addr.address = None
            self.assertIsNone(ip_addr.address)
            session.session.commit()

    def test_0040_delete_subnet(self):
        ip_addr = self.pick_ip()

        with self.assertRaises(IntegrityError):
            ip_addr.subnet = None
            self.assertIsNone(ip_addr.subnet)
            session.session.commit()


class TestIpEvents(IpModelTestBase):
    def test_0010_correct_subnet_and_ip(self):
        ip_address, _ = get_free_ip((self.subnet, ))

        ip = host.IP(interface=self.interface, address=ip_address, subnet=self.subnet)
        session.session.add(ip)
        session.session.commit()

        ip_address, _ = get_free_ip((self.subnet, ))
        ip = host.IP(address=ip_address, subnet=self.subnet, interface=self.interface)
        session.session.add(ip)
        session.session.commit()

        host.IP.q.filter(host.IP.interface == self.interface).delete()
        session.session.commit()

    def test_0020_missing_subnet(self):
        ip_address, _ = get_free_ip((self.subnet, ))
        ip = host.IP(interface=self.interface, address=ip_address)

        with self.assertRaises(IntegrityError):
            session.session.add(ip)
            session.session.commit()

    def test_0030_missing_ip(self):
        ip = host.IP(interface=self.interface, subnet=self.subnet)

        with self.assertRaises(IntegrityError):
            session.session.add(ip)
            session.session.commit()

    def test_0040_wrong_subnet(self):
        ip_address, _ = get_free_ip((self.subnets[0], ))

        ip = host.IP(interface=self.interface, address=ip_address)

        with self.assertRaises(ValueError):
            ip.subnet = self.subnets[1]

        ip = host.IP(interface=self.interface, subnet=self.subnets[1])

        with self.assertRaises(ValueError):
            ip.address = ip_address

        with self.assertRaises(ValueError):
            host.IP(interface=self.interface, subnet=self.subnets[1], address=ip_address)


class Test_060_Cascades(FixtureDataTestBase):
    datasets = (SubnetData, UserData, HostData, InterfaceData, IPData,
                TrafficVolumeData, SwitchPortData)

    def test_0010_cascade_on_delete_ip(self):
        test_ip = host.IP.q.filter_by(
            address=IPData.dummy_user_ipv4.address).one()
        tv_of_test_ip = test_ip.traffic_volumes
        session.session.delete(test_ip)
        session.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in tv_of_test_ip))

    def test_0010_cascade_on_delete_interface(self):
        test_interface = host.Interface.q.filter_by(
            mac=InterfaceData.dummy.mac).one()
        ips = test_interface.ips
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        session.session.delete(test_interface)
        session.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in chain(ips, traffic_volumes)))

    def test_0010_cascade_on_delete_host(self):
        test_host = host.Host.q.first()
        interfaces = test_host.interfaces
        ips = tuple(chain(*(d.ips for d in interfaces)))
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        session.session.delete(test_host)
        session.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in chain(interfaces, ips, traffic_volumes)))

    def test_0010_cascade_on_delete_user(self):
        test_user = user.User.q.filter_by(login=UserData.dummy.login).one()
        hosts = test_user.hosts
        interfaces = tuple(chain(*(h.interfaces for h in hosts)))
        ips = tuple(chain(*(d.ips for d in interfaces)))
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        session.session.delete(test_user)
        session.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in chain(hosts, interfaces, ips, traffic_volumes)))

    def test_cascade_on_delete_vlan(self):
        # TODO: delete a vlan
        vlan = VLAN.q.filter_by(vid=VLANData.vlan_dummy1.vid).one()
        associations_query = session.session.query(host.switch_port_default_vlans)\
            .filter_by(vlan_id=vlan.id)

        self.assertEqual(associations_query.count(), 2)
        for subnet in vlan.subnets:
            session.session.delete(subnet)
        session.session.delete(vlan)
        session.session.commit()
        self.assertEqual(associations_query.count(), 0)

    def test_cascade_on_delete_switch_port(self):
        port_name = SwitchPortData.dummy_port4.name
        port = host.SwitchPort.q.filter_by(name=port_name).one()
        associations_query = session.session.query(host.switch_port_default_vlans)\
            .filter_by(switch_port_id=port.id)

        self.assertEqual(associations_query.count(), 2)
        session.session.delete(port)
        session.session.commit()
        self.assertEqual(associations_query.count(), 0)


class TestVLANAssociations(FixtureDataTestBase):
    datasets = (SwitchPortData,)

    def test_secondary_relationship_works(self):
        port = host.SwitchPort.q.filter_by(name=SwitchPortData.dummy_port1.name).one()
        self.assertEqual(len(port.default_vlans), 1)
        port4 = host.SwitchPort.q.filter_by(name=SwitchPortData.dummy_port4.name).one()
        self.assertEqual(len(port4.default_vlans), 2)
