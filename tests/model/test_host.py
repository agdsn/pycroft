# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import chain

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.base import object_state

from pycroft.lib.net import get_free_ip
from pycroft.model.host import Interface, IP, switch_port_default_vlans
from pycroft.model.types import InvalidMACAddressException
from .. import factories


class TestInterfaceValidators:
    @pytest.fixture(scope='class')
    def host(self, class_session):
        return factories.HostFactory()

    @pytest.mark.parametrize('mac', [
        'ff:ff:ff:ff:ff',
        "ff:ff:ff:ff:ff:ff",
        "ff:asjfjsdaf:ff:ff:ff:ff",
        "aj:00:ff:1f:ff:ff",
        "ff:ff:ff:ff:ff:ff:ff",
    ])
    def test_bad_macs(self, session, host, mac):
        interface = Interface(host=host)
        assert object_state(interface).transient

        with pytest.raises(InvalidMACAddressException):
            interface.mac = mac
        with pytest.raises(IntegrityError):
            session.add(interface)
            session.flush()

    @pytest.mark.parametrize('mac', [
        "00:00:00:01:00:00",
    ])
    def test_good_macs(self, session, host, mac):
        interface = Interface(host=host)
        assert object_state(interface).transient

        interface.mac = mac
        session.add(interface)
        session.flush()


class TestIpModel:
    @pytest.fixture(scope='class')
    def subnet(self, class_session):
        return factories.SubnetFactory.create()

    @pytest.fixture(scope='class')
    def subnet2(self, class_session):
        return factories.SubnetFactory.create()

    @pytest.fixture(scope='class')
    def interface(self, class_session):
        return factories.InterfaceFactory()

    @pytest.fixture(scope='class')
    def ip_addr(self, class_session, subnet, interface):
        ip, _ = get_free_ip((subnet,))
        addr = IP(interface=interface, address=ip, subnet=subnet)
        class_session.add(addr)
        return addr

    def test_delete_address(self, session, ip_addr):
        with pytest.raises(IntegrityError):
            ip_addr.address = None
            assert ip_addr.address is None
            session.flush()

    def test_delete_subnet(self, session, ip_addr):
        with pytest.raises(IntegrityError):
            ip_addr.subnet = None
            assert ip_addr.subnet is None
            session.flush()

    def test_correct_subnet_and_ip(self, session, subnet, interface):
        ip_address, _ = get_free_ip((subnet, ))

        with session.begin_nested():
            session.add(IP(interface=interface, address=ip_address, subnet=subnet))

        ip_address, _ = get_free_ip((subnet, ))
        with session.begin_nested():
            session.add(IP(address=ip_address, subnet=subnet, interface=interface))

        with session.begin_nested():
            IP.q.filter(IP.interface == interface).delete()

    def test_missing_subnet(self, session, interface, subnet):
        ip_address, _ = get_free_ip((subnet, ))
        ip = IP(interface=interface, address=ip_address)
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(ip)

    def test_missing_ip(self, session, interface, subnet):
        with pytest.raises(IntegrityError), session.begin_nested():
            session.add(IP(interface=interface, subnet=subnet))

    def test_wrong_subnet(self, interface, subnet, subnet2):
        ip_address, _ = get_free_ip((subnet, ))

        ip = IP(interface=interface, address=ip_address)

        with pytest.raises(ValueError):
            ip.subnet = subnet2

        ip = IP(interface=interface, subnet=subnet2)

        with pytest.raises(ValueError):
            ip.address = ip_address

        with pytest.raises(ValueError):
            IP(interface=interface, subnet=subnet2, address=ip_address)


class TestVariousCascades:
    @pytest.fixture(scope='class')
    def user(self, class_session):
        user = factories.UserFactory.build(with_host=True)
        class_session.add(user)
        return user

    @pytest.fixture(scope='class')
    def host(self, user):
        return user.hosts[0]

    @pytest.fixture(scope='class')
    def interface(self, host):
        return host.interfaces[0]

    @pytest.fixture(scope='class')
    def ips(self, class_session, interface):
        ips = factories.IPFactory.create_batch(3, interface=interface)
        # there's probably a better way to do this, e.g. by introducing an `IpWithTrafficFactory`
        for ip in ips:
            factories.TrafficVolumeFactory.create_batch(4, ip=ip)
        return ips

    @pytest.fixture(scope='class')
    def ip(self, ips):
        return ips[0]

    def test_traffic_volume_cascade_on_delete_ip(self, ip, session):
        test_ip = ip
        tv_of_test_ip = test_ip.traffic_volumes
        with session.begin_nested():
            session.delete(test_ip)
        assert all(inspect(o).was_deleted for o in tv_of_test_ip)

    def test_traffic_volume_cascade_on_delete_interface(self, session, user, interface, ips):
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        with session.begin_nested():
            session.delete(interface)
        assert all(inspect(o).was_deleted for o in chain(ips, traffic_volumes))

    def test_traffic_volume_cascade_on_delete_host(self, session, host):
        test_host = host
        interfaces = test_host.interfaces
        ips = tuple(chain(*(d.ips for d in interfaces)))
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        with session.begin_nested():
            session.delete(test_host)
        assert all(inspect(o).was_deleted for o in chain(interfaces, ips, traffic_volumes))

    def test_all_cascades_on_delete_user(self, session, user):
        """Test that hosts, interfaces, ips, and traffic_volumes of a host are cascade deleted"""
        test_user = user
        hosts = test_user.hosts
        interfaces = tuple(chain(*(h.interfaces for h in hosts)))
        ips = tuple(chain(*(d.ips for d in interfaces)))
        traffic_volumes = tuple(chain(*(ip.traffic_volumes for ip in ips)))
        with session.begin_nested():
            session.delete(test_user)
        assert all(inspect(o).was_deleted for o in chain(hosts, interfaces, ips, traffic_volumes))


class TestDefaultVlanCascades:
    @pytest.fixture(scope='class')
    def vlans(self, class_session):
        return factories.VLANFactory.create_batch(2)

    @pytest.fixture(scope='class')
    def vlan(self, vlans):
        return vlans[0]

    # autouse because this provides the `default_vlans`
    @pytest.fixture(scope='class', autouse=True)
    def ports(self, vlans):
        return factories.SwitchPortFactory.create_batch(2, default_vlans=vlans)

    @pytest.fixture(scope='class')
    def port(self, ports):
        return ports[0]

    def test_default_vlan_associations_cascade_on_delete_vlan(self, session, vlan):
        associations_query = session.query(switch_port_default_vlans)\
            .filter_by(vlan_id=vlan.id)

        assert associations_query.count() == 2
        for subnet in vlan.subnets:
            session.delete(subnet)
        session.delete(vlan)
        assert associations_query.count() == 0

    def test_default_vlan_associations_cascade_on_delete_switch_port(self, session, port):
        associations_query = session.query(switch_port_default_vlans)\
            .filter_by(switch_port_id=port.id)

        assert associations_query.count() == 2
        session.delete(port)
        session.flush()
        assert associations_query.count() == 0


class TestVLANAssociations:
    def test_secondary_relationship_works(self, session):
        vlans = factories.VLANFactory.create_batch(2)
        port1 = factories.SwitchPortFactory(default_vlans=vlans[:1])
        assert len(port1.default_vlans) == 1
        port2 = factories.SwitchPortFactory(default_vlans=vlans)
        assert len(port2.default_vlans) == 2
