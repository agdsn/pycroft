# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from fixtures.host_aliases_fixture import ARecordData, AAAARecordData, \
    MXRecordData, CNameRecordData, NSRecordData, IpData
from tests import FixtureDataTestBase, OldPythonTestCase
from pycroft import model
from pycroft.model.hosts import ARecord, AAAARecord, Ip

class Test_010_ARecordValidator(FixtureDataTestBase):

    datasets = [ARecordData, IpData]

    def test_0010_ip_validate(self):
        record =  ARecord.q.first()

        def set_ip(ip):
            record.ip = ip

        ips = Ip.q.all()

        for ip in ips:
            if ip.subnet.ip_type == "6":
                self.assertRaises(AssertionError, set_ip, ip)
                break

class Test_020_AAAARecordValidator(FixtureDataTestBase):

    datasets = [AAAARecordData, IpData]

    def test_0010_ip_validate(self):
        record =  AAAARecord.q.first()

        def set_ip(ip):
            record.ip = ip

        ips = Ip.q.all()

        for ip in ips:
            if ip.subnet.ip_type == "4":
                self.assertRaises(AssertionError, set_ip, ip)
                break
