# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re
from itertools import chain

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from pycroft.lib.net import get_free_ip
from pycroft.model import host
from pycroft.model.types import InvalidMACAddressException
from tests import FactoryDataTestBase
from .. import factories


class TestInterfaceValidators(FactoryDataTestBase):
    mac_regex = re.compile(r"^[a-f0-9]{2}(:[a-f0-9]{2}){5}$")

    def create_factories(self):
        super().create_factories()
        self.host = factories.HostFactory()

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
        self.session.add(interface)
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()

        # Assert a correct mac
        self.assertSetMAC(interface, "00:00:00:01:00:00")

        # Assert that we have the mac assigned
        self.session.add(interface)
        self.session.commit()

        # Wipe the instance
        self.session.delete(interface)
        self.session.commit()

class IpModelTestBase(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.subnets = factories.SubnetFactory.create_batch(5)
        self.subnet = self.subnets[0]
        self.interface = factories.InterfaceFactory()

    def pick_ip(self):
        ip, _ = get_free_ip((self.subnet,))
        addr = host.IP(interface=self.interface, address=ip, subnet=self.subnet)
        self.session.add(addr)
        self.session.commit()
        return addr


class TestIpModel(IpModelTestBase):
    def test_delete_address(self):
        ip_addr = self.pick_ip()

        with self.assertRaises(IntegrityError):
            ip_addr.address = None
            self.assertIsNone(ip_addr.address)
            self.session.commit()

    def test_delete_subnet(self):
        ip_addr = self.pick_ip()

        with self.assertRaises(IntegrityError):
            ip_addr.subnet = None
            self.assertIsNone(ip_addr.subnet)
            self.session.commit()


class TestIpEvents(IpModelTestBase):
    def test_correct_subnet_and_ip(self):
        ip_address, _ = get_free_ip((self.subnet, ))

        ip = host.IP(interface=self.interface, address=ip_address, subnet=self.subnet)
        self.session.add(ip)
        self.session.commit()

        ip_address, _ = get_free_ip((self.subnet, ))
        ip = host.IP(address=ip_address, subnet=self.subnet, interface=self.interface)
        self.session.add(ip)
        self.session.commit()

        host.IP.q.filter(host.IP.interface == self.interface).delete()
        self.session.commit()

    def test_missing_subnet(self):
        ip_address, _ = get_free_ip((self.subnet, ))
        ip = host.IP(interface=self.interface, address=ip_address)

        with self.assertRaises(IntegrityError):
            self.session.add(ip)
            self.session.commit()

    def test_missing_ip(self):
        ip = host.IP(interface=self.interface, subnet=self.subnet)

        with self.assertRaises(IntegrityError):
            self.session.add(ip)
            self.session.commit()

    def test_wrong_subnet(self):
        ip_address, _ = get_free_ip((self.subnets[0], ))

        ip = host.IP(interface=self.interface, address=ip_address)

        with self.assertRaises(ValueError):
            ip.subnet = self.subnets[1]

        ip = host.IP(interface=self.interface, subnet=self.subnets[1])

        with self.assertRaises(ValueError):
            ip.address = ip_address

        with self.assertRaises(ValueError):
            host.IP(interface=self.interface, subnet=self.subnets[1], address=ip_address)


class TestVariousCascades(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.user = factories.UserWithHostFactory()
        self.host = self.user.hosts[0]
        self.interface = self.host.interfaces[0]
        ips = factories.IPFactory.create_batch(3, interface=self.interface)
        # there's probably a better way to do this, e.g. by introducing an `IpWithTrafficFactory`
        for ip in ips:
            factories.TrafficVolumeFactory.create_batch(4, ip=ip)
        self.ip = self.interface.ips[0]


    def test_traffic_volume_cascade_on_delete_ip(self):
        test_ip = self.ip
        tv_of_test_ip = test_ip.traffic_volumes
        self.session.delete(test_ip)
        self.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in tv_of_test_ip))

    def test_traffic_volume_cascade_on_delete_interface(self):
        test_interface = self.interface
        ips = test_interface.ips
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        self.session.delete(test_interface)
        self.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in chain(ips, traffic_volumes)))

    def test_traffic_volume_cascade_on_delete_host(self):
        test_host = self.host
        interfaces = test_host.interfaces
        ips = tuple(chain(*(d.ips for d in interfaces)))
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        self.session.delete(test_host)
        self.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in chain(interfaces, ips, traffic_volumes)))

    def test_all_cascades_on_delete_user(self):
        """Test that hosts, interfaces, ips, and traffic_volumes of a host are cascade deleted"""
        test_user = self.user
        hosts = test_user.hosts
        interfaces = tuple(chain(*(h.interfaces for h in hosts)))
        ips = tuple(chain(*(d.ips for d in interfaces)))
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        self.session.delete(test_user)
        self.session.commit()
        self.assertTrue(all(inspect(o).was_deleted
                            for o in chain(hosts, interfaces, ips, traffic_volumes)))


class TestDefaultVlanCascades(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        # We need: SwitchPort <- `switch_port_default_vlans` -> Vlan
        self.vlans = factories.VLANFactory.create_batch(2)
        self.vlan = self.vlans[0]
        self.ports = factories.SwitchPortFactory.create_batch(2, default_vlans=self.vlans)
        self.port = self.ports[0]

    def test_default_vlan_associations_cascade_on_delete_vlan(self):
        associations_query = self.session.query(host.switch_port_default_vlans)\
            .filter_by(vlan_id=self.vlan.id)

        self.assertEqual(associations_query.count(), 2)
        for subnet in self.vlan.subnets:
            self.session.delete(subnet)
        self.session.delete(self.vlan)
        self.session.commit()
        self.assertEqual(associations_query.count(), 0)

    def test_default_vlan_associations_cascade_on_delete_switch_port(self):
        associations_query = self.session.query(host.switch_port_default_vlans)\
            .filter_by(switch_port_id=self.port.id)

        self.assertEqual(associations_query.count(), 2)
        self.session.delete(self.port)
        self.session.commit()
        self.assertEqual(associations_query.count(), 0)


class TestVLANAssociations(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.vlans = factories.VLANFactory.create_batch(2)
        self.port1 = factories.SwitchPortFactory(default_vlans=self.vlans[:1])
        self.port2 = factories.SwitchPortFactory(default_vlans=self.vlans)

    def test_secondary_relationship_works(self):
        self.assertEqual(len(self.port1.default_vlans), 1)
        self.assertEqual(len(self.port2.default_vlans), 2)
