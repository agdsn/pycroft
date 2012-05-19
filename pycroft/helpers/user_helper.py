# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.helpers.user_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2011 by AG DSN.
"""

import random
import ipaddr
from pycroft.model import hosts
from pycroft.model.session import session


class SubnetFullException(Exception):
    pass


def generatePassword(length):
    allowedLetters = "abcdefghijklmnopqrstuvwxyz!$%&()=.,"\
                     ":;-_#+1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    passwordLength = length
    password = ""
    for i in range(passwordLength):
        password += allowedLetters[random.choice(range(len
            (allowedLetters)))]
    return password


def generateHostname(ip_address, hostname):
    if hostname == "":
        return "whdd" + ip_address.split(u".")[-1]
    return hostname


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
