# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.helpers.host_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2012 by AG DSN.
"""
import ipaddr
import re
from pycroft.model import hosts
from pycroft.model.session import session


def sort_ports(ports):
    number_re = re.compile(r"[0-9]+")
    letter_re = re.compile(r"[a-z]")

    def make_sort_key(port):
        number = number_re.search(port.name)
        letter = letter_re.search(port.name.lower())

        return int(number.group(0)) + 1024 * ord(letter.group(0))

    sorted_ports = sorted(ports, key=make_sort_key)

    return sorted_ports


def generate_hostname(ip_address):
    return "whdd" + ip_address.split(u".")[-1]


class SubnetFullException(Exception):
    pass


def get_free_ip(subnets):
    for subnet in subnets:
        reserved = subnet.reserved_addresses
        net = ipaddr.IPv4Network(subnet.address)
        used_ips = [dev.ipv4 for dev in subnet.net_devices]

        if (net.numhosts - reserved) <= 0:
            continue

        for ip in net.iterhosts():
            if reserved > 0:
                reserved += -1
                continue
            if ip.compressed not in used_ips:
                return ip.compressed

    raise SubnetFullException()


def select_subnet_for_ip(ip, subnets):
    for subnet in subnets:
        if ipaddr.IPAddress(ip) in ipaddr.IPv4Network(subnet.address):
            return subnet

