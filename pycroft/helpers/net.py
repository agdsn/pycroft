# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import re

# Byte represented by 2 hexadecimal digits
BYTE_PATTERN = r'(?:[a-fA-F0-9]{2})'
# Pattern for the most significant byte
# Does not allow the first bit to be set (multicast flag)
MOST_SIGNIFICANT_BYTE_PATTERN = r'(?:[a-fA-F0-9][02468ACE])'
# Allowed 1 byte separators
SEP1_PATTERN = r'[-:]'
# Allowed 2 byte separators
SEP2_PATTERN = r'\.'
# Allowed 3 byte separators
SEP3_PATTERN = r'-'


"""Regular expression object for matching MAC addresses in different formats.
A valid MAC address is a sequence of 6 bytes coded as hexadecimal digits
separated by a symbol after either one, two or three bytes. It is also possible
that there is no separating symbol.

The following examples all encode the same MAC address:
001122334455
00-11-22-33-44-55
00:11:22:33:44:55
0011.2233.4455
001122-334455

After a successful match, the individual bytes bytes, as well as the
separator symbols can be accessed using symbolic group names.
byte1, byte2, byte3, byte4, byte5, byte6: The n-th byte
sep1, sep2, sep3: The one, two or three byte separator char or None
"""
mac_regex = re.compile(r"""
    # MAC-Addresses are in big endian, hence we rightmost is the highest
    # byte.

    # Begin of string:
    \A
    # First, most significant byte:
    (?P<byte1>{BYTE_PATTERN})
    # Try to match sep1 between 1 and 2:
    (?P<sep1>{SEP1_PATTERN})?
    # Second byte:
    (?P<byte2>{BYTE_PATTERN})
    # If sep1 has matched previously, it must also match between 2 and 3,
    # else try to match sep2:
    (?(sep1)(?P=sep1)|(?P<sep2>{SEP2_PATTERN})?)
    # Third byte:
    (?P<byte3>{BYTE_PATTERN})
    # If sep1 has matched previously, it must also match between 3 and 4, if
    # sep2 has matched previously, there must not be a separator here, else
    # try to match sep3:
    (?(sep1)(?P=sep1)|(?(sep2)|(?P<sep3>{SEP3_PATTERN})?))
    # Fourth byte:
    (?P<byte4>{BYTE_PATTERN})
    # If sep1 has matched previously, it must also match between 4 and 5.
    # The same applies to sep2:
    (?(sep1)(?P=sep1))(?(sep2)(?P=sep2))
    # Fifth byte:
    (?P<byte5>{BYTE_PATTERN})
    # If sep1 has matched previously, it must also match between 5 and 6:
    (?(sep1)(?P=sep1))
    # Sixth, least significant byte:
    (?P<byte6>{BYTE_PATTERN})
    # End of string:
    \Z
""".format(**globals()), re.VERBOSE | re.IGNORECASE)


def sort_ports(ports):
    number_re = re.compile(r"[0-9]+")
    letter_re = re.compile(r"[a-z]")

    def make_sort_key(port):
        number = number_re.search(port.name)
        letter = letter_re.search(port.name.lower())

        return int(number.group(0)) + 1024 * ord(letter.group(0))

    sorted_ports = sorted(ports, key=make_sort_key)

    return sorted_ports
