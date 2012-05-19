# -*- coding: utf-8 -*-
"""
    pycroft.helpers.host_helper
    ~~~~~~~~~~~~~~

    :copyright: (c) 2012 by AG DSN.
"""
import re


def sort_ports(ports):
    number_re = re.compile(r"[0-9]+")
    letter_re = re.compile(r"[a-z]")

    def make_sort_key(port):
        number = number_re.search(port.name)
        letter = letter_re.search(port.name.lower())

        return int(number.group(0)) + 1024 * ord(letter.group(0))

    sorted_ports = sorted(ports, key=make_sort_key)

    return sorted_ports
