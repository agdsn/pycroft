# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import islice, ifilter
import ipaddr


class SubnetFullException(Exception):
    pass


class MacExistsException(Exception):
    pass


def get_free_ip(subnets):
    for subnet in subnets:
        reserved = subnet.reserved_addresses or 0
        net = ipaddr.IPNetwork(subnet.address)
        used_ips = frozenset(ipaddr.IPAddress(ip.address) for ip in subnet.ips)
        unreserved = islice(net.iterhosts(), reserved, None)
        unused = ifilter(lambda ip: ip not in used_ips, unreserved)
        try:
            return next(unused).compressed
        except StopIteration:
            continue

    raise SubnetFullException()


def select_subnet_for_ip(ip, subnets):
    for subnet in subnets:
        if ipaddr.IPAddress(ip) in ipaddr.IPNetwork(subnet.address):
            return subnet
