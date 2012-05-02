# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    web.blueprints.user.helpers
    ~~~~~~~~~~~~~~

    This module provides the following helpers for /user:
    - password generator
    - getRegex checker

    :copyright: (c) 2012 by AG DSN.
"""

import random, ipaddr
from pycroft.model import hosts, session

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
        return "whdd" + ip_address[-3, -1]
    return hostname


def getRegex(type):
    regexName = "^(([a-z]{1,5}|[A-Z][a-z0-9]+)\\s)*([A-Z][a-z0-9]+)((-|\\s)"\
                "[A-Z][a-z0-9]+|\\s[a-z]{1,5})*$"
    regexLogin = "^[a-z][a-z0-9_]{1,20}[a-z0-9]$"
    regexMac = "^[a-f0-9]{2}(:[a-f0-9]{2}){5}$"
    regexRoom = "^[0-9]{1,6}$"

    if type == "name":
        return regexName
    if type == "login":
        return regexLogin
    if type == "mac":
        return regexMac
    if type == "room":
        return regexRoom


def getFreeIP(subnets):
    possible_hosts = []

    for subnet in subnets:
        for ip in ipaddr.IPv4Network(subnet).iterhosts():
            possible_hosts.append(ip)

    reserved_hosts = []

    reserved_hosts_string = session.session.query(hosts.NetDevice.ipv4).all()

    for ip in reserved_hosts_string:
        reserved_hosts.append(ipaddr.IPv4Address(ip.ipv4))

    for ip in reserved_hosts:
        if ip in possible_hosts:
            possible_hosts.remove(ip)

    if possible_hosts:
        return possible_hosts[0].compressed

    raise SubnetFullException()
