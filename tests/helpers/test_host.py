# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from random import shuffle

import netaddr
import pytest

from pycroft.helpers.net import port_name_sort_key
from pycroft.lib.host import change_mac, generate_hostname
from pycroft.lib.net import SubnetFullException, get_free_ip
from pycroft.model.host import IP
from tests import factories


@pytest.fixture
def port_names():
    return [f"{let}{num}" for let in "ABCDEFG" for num in range(1, 24)]


@pytest.fixture
def shuffled_port_names(port_names):
    shuffled = port_names.copy()
    shuffle(shuffled)
    return shuffled


def test_port_sorting(port_names, shuffled_port_names):
    assert sorted(shuffled_port_names, key=port_name_sort_key) == port_names


@pytest.mark.parametrize(
    "address, expected",
    [
        (
            netaddr.IPAddress(f"{byte1:d}.{byte2:d}.{byte3:d}.{byte4:d}"),
            f"x{byte1:02x}{byte2:02x}{byte3:02x}{byte4:02x}",
        )
        for byte1, byte2, byte3, byte4 in [(141, 30, 228, 10), (10, 10, 10, 1), (127, 0, 0, 1)]
    ],
)
def test_hostname_generation(address: netaddr.IPAddress, expected: str):
    assert generate_hostname(address) == expected


@pytest.fixture
def subnets(session):
    return factories.SubnetFactory.create_batch(10)


@pytest.fixture(params=list(range(10)))
def subnet(subnets, request):
    return subnets[request.param]


@pytest.fixture
def host(session):
    return factories.HostFactory()


def test_get_free_ip_simple(session, subnet):
    # TODO this has nothing to do with the helpers.
    ip, subnet2 = get_free_ip((subnet,))
    assert subnet2 == subnet
    assert ip in subnet.address


@pytest.fixture
def interface():
    return factories.InterfaceFactory.build()


@pytest.fixture
def build_full_subnet(interface):
    def _build():
        net = factories.SubnetFactory.build()
        from pycroft.model._all import Subnet

        assert isinstance(net, Subnet)
        net.ips.extend(
            IP(address=ip, subnet=net, interface=interface) for ip in net.usable_ip_range
        )
        return net
    return _build


@pytest.fixture
def full_subnet(build_full_subnet):
    return build_full_subnet()


@pytest.fixture
def empty_subnet():
    return factories.SubnetFactory.build()


def test_no_free_ip_in_full_subnet(full_subnet):
    with pytest.raises(SubnetFullException):
        get_free_ip((full_subnet,))


def test_free_ip_with_one_subnet_empty(full_subnet, empty_subnet):
    try:
        get_free_ip((full_subnet, empty_subnet))
    except SubnetFullException:
        pytest.fail("Subnets should have free IPs.")


def test_no_free_ip_with_two_full_subnets(build_full_subnet):
    with pytest.raises(SubnetFullException):
        get_free_ip((build_full_subnet(), build_full_subnet()))


def test_change_mac(session):
    with session.begin_nested():
        processing_user = factories.UserFactory()
        interface = factories.InterfaceFactory()
    new_mac = "20:00:00:00:00:00"

    change_mac(interface, new_mac, processing_user)

    assert interface.mac == new_mac
