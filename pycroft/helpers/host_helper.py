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


def getFreeIP(subnets):
    possible_hosts = []

    for subnet in subnets:
        for ip in ipaddr.IPv4Network(subnet.address).iterhosts():
            possible_hosts.append(ip)

    reserved_hosts = []

    reserved_hosts_string = session.query(hosts.NetDevice.ipv4).all()

    for ip in reserved_hosts_string:
        reserved_hosts.append(ipaddr.IPv4Address(ip.ipv4))

    for ip in reserved_hosts:
        if ip in possible_hosts:
            possible_hosts.remove(ip)

    if possible_hosts:
        return possible_hosts[0].compressed

    raise SubnetFullException()

