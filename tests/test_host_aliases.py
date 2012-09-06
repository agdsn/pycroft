# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from fixtures.host_aliases_fixture import ARecordData, AAAARecordData,\
    MXRecordData, CNameRecordData, NSRecordData, IpData
from tests import FixtureDataTestBase
from pycroft.model.hosts import ARecord, AAAARecord, MXRecord, CNameRecord,\
    NSRecord, Ip

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

class Test_030_GenEntryMethods(FixtureDataTestBase):

    datasets = [ARecordData, AAAARecordData, MXRecordData, CNameRecordData,\
    NSRecordData]

    def test_0010_arecord_without_ttl(self):
        record = ARecord.q.filter(ARecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"%s IN A %s" % (record.content, record.ip.address)

        self.assertEqual(entry, entry_expected)

    def test_0015_arecord_with_ttl(self):
        record = ARecord.q.filter(ARecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"%s %s IN A %s" % (record.content, record.time_to_live,\
                                             record.ip.address)

        self.assertEqual(entry, entry_expected)

    def test_0020_aaaarecord_without_ttl(self):
        record = AAAARecord.q.filter(AAAARecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"%s IN AAAA %s" % (record.content, record.ip.address)

        self.assertEqual(entry, entry_expected)

    def test_0025_aaaarecord_with_ttl(self):
        record = AAAARecord.q.filter(AAAARecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"%s %s IN AAAA %s" % (record.content,\
                                                record.time_to_live, record.ip.address)

        self.assertEqual(entry, entry_expected)

    def test_0030_mxrecord(self):
        record = MXRecord.q.first()
        entry = record.gen_entry
        entry_expected = u"%s IN MX %s %s" % (record.domain, record.priority, record.content)

        self.assertEqual(entry, entry_expected)

    def test_0040_cnamerecord(self):
        record = CNameRecord.q.first()
        entry = record.gen_entry
        entry_expected = u"%s IN CNAME %s" % (record.content, record.alias_for)

        self.assertEqual(entry, entry_expected)

    def test_0050_nsrecord_without_ttl(self):
        record = NSRecord.q.filter(NSRecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"%s IN NS %s" % (record.domain, record.content)

        self.assertEqual(entry, entry_expected)

    def test_0055_nsrecord_with_ttl(self):
        record = NSRecord.q.filter(NSRecord.time_to_live != None).first()
        entry =  record.gen_entry
        entry_expected = u"%s %s IN NS %s" % (record.domain, record.time_to_live, \
                                              record.content)
