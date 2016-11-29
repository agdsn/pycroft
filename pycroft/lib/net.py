# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import division
from itertools import islice
from ipaddr import IPv4Address, IPv6Address, IPv4Network, IPv6Network

from pycroft._compat import ifilter


class SubnetFullException(Exception):
    message = "Subnet full"


class MacExistsException(Exception):
    message = "MAC exists"


def get_free_ip(subnets):
    for subnet in subnets:
        reserved = subnet.reserved_addresses or 0
        used_ips = frozenset(ip.address for ip in subnet.ips)
        unreserved = islice(subnet.address.iterhosts(), reserved, None)
        unused = ifilter(lambda ip: ip not in used_ips, unreserved)
        try:
            return next(unused), subnet
        except StopIteration:
            continue

    raise SubnetFullException()


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

