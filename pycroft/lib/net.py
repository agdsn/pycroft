# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import islice
from ipaddr import IPv4Address, IPv6Address, IPv4Network, IPv6Network
import sys


class SubnetFullException(Exception):
    def __init__(self):
        super().__init__("Subnet full")


class MacExistsException(Exception):
    def __init__(self):
        super().__init__("MAC address already exists")


def get_subnet_unused_ips(subnet):
    reserved_bottom = subnet.reserved_addresses_bottom or 0
    reserved_top = subnet.reserved_addresses_top or 0
    used_ips = frozenset(ip.address for ip in subnet.ips)
    unreserved = islice(
        subnet.address.iterhosts(), reserved_bottom,
        # Stop argument must be None or an integer: 0 <= x <= sys.maxsize.
        # IPv6 subnets can exceed this boundary on 32 bit python builds.
        min(subnet.address.numhosts - reserved_top - 2, sys.maxsize))
    return (ip for ip in unreserved if ip not in used_ips)


def get_unused_ips(subnets):
    return {subnet: get_subnet_unused_ips(subnet) for subnet in subnets}


def get_free_ip(subnets):
    unused = get_unused_ips(subnets)

    for subnet, ips in unused.items():
        try:
            ip = next(ips)

            if ip is not None and subnet is not None:
                return ip, subnet
        except StopIteration:
            continue

    raise SubnetFullException()


#TODO: Implement this in the model
def get_subnets_for_room(room):
    return [s for p in room.connected_patch_ports
               for v in p.switch_port.default_vlans
               for s in v.subnets
               if s.address.version == 4]


def ptr_name(network, ip_address):
    """
    :param IPv4Network|IPv6Network network:
    :param IPv4Address|IPv6Address ip_address:
    :rtype: str
    :return:
    """
    hostbits = network.max_prefixlen - network.prefixlen
    if isinstance(ip_address, IPv4Address):
        num_octets = min((hostbits + 7 // 8), 1)
        reversed_octets = reversed(ip_address.exploded.split('.'))
        return '.'.join(islice(reversed_octets, num_octets))
    elif isinstance(ip_address, IPv6Address):
        num_chars = min((hostbits + 3 // 4), 1)
        reversed_chars = reversed(ip_address.exploded.replace(':', ''))
        return '.'.join(islice(reversed_chars, num_chars))
    raise TypeError()
