# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
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
