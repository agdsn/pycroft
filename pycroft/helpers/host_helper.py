# -*- coding: utf-8 -*-
"""
    pycroft.helpers.host_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2012 by AG DSN.
"""
import re

def sort_port_key(port):
    number = re.search("[0-9]+", port.name)
    letter = re.search("[a-z]", port.name.lower())

    return int(number.group(0)) + 1024 * ord(letter.group(0))


def sort_ports(ports):
    sorted_ports = sorted(ports,
        key=lambda port: sort_port_key(port))

    return sorted_ports
