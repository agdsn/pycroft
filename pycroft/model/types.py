# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from __future__ import absolute_import
import ipaddr
from sqlalchemy import String, TypeDecorator
from sqlalchemy.dialects.postgresql import MACADDR, INET
from pycroft.helpers.net import mac_regex


class _IPType(TypeDecorator):
    impl = String(50)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(INET)
        else:
            return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)


class IPAddress(_IPType):
    def python_type(self):
        return ipaddr._BaseIP

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return ipaddr.IPAddress(value)


class IPNetwork(_IPType):
    def python_type(self):
        return ipaddr._BaseNet

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return ipaddr.IPNetwork(value)


class MACAddress(TypeDecorator):
    impl = String(10)

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(MACADDR)
        else:
            return dialect.type_descriptor(self.impl)

    def process_result_value(self, value, dialect):
        if dialect.name == 'postgresql':
            return value
        return "{}:{}:{}:{}:{}:{}".format(value[0:2], value[2:4], value[4:6],
                                          value[6:8], value[8:10], value[10:12])

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        m = mac_regex.match(value)
        if m is None:
            print repr(value)
            print mac_regex.pattern
            raise ValueError('"{}" is not a valid MAC address.'.format(value))
        groups = m.groupdict()
        return "".join((groups["byte1"], groups["byte2"], groups["byte3"],
                        groups["byte4"], groups["byte5"], groups["byte6"]))

    def python_type(self):
        return str


class InvalidMACAddressException(ValueError):
    pass
