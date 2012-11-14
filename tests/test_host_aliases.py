# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from fixtures.host_aliases_fixture import ARecordData, AAAARecordData,\
    MXRecordData, CNameRecordData, NSRecordData, SRVRecordData, IpData, UserHostData, UserNetDeviceData
from tests import FixtureDataTestBase
from pycroft.model.hosts import ARecord, AAAARecord, MXRecord, CNameRecord,\
    NSRecord, SRVRecord, Ip
import ipaddr

class Test_010_ARecordValidator(FixtureDataTestBase):

    datasets = [ARecordData, IpData]

    def test_0010_ip_validate(self):
        record =  ARecord.q.first()

        def set_ip(ip):
            record.address = ip

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
            record.address = ip

        ips = Ip.q.all()

        for ip in ips:
            if ip.subnet.ip_type == "4":
                self.assertRaises(AssertionError, set_ip, ip)
                break

class Test_030_GenEntryMethods(FixtureDataTestBase):

    datasets = [ARecordData, AAAARecordData, MXRecordData, CNameRecordData, NSRecordData, SRVRecordData]

    def test_0010_arecord_without_ttl(self):
        record = ARecord.q.filter(ARecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"%s IN A %s" % (record.name, record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"%s.in-addr.arpa. IN PTR %s" % (".".join(reversed(record.address.address.split("."))), record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0015_arecord_with_ttl(self):
        record = ARecord.q.filter(ARecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"%s %s IN A %s" % (record.name, record.time_to_live, record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"%s.in-addr.arpa. %s IN PTR %s" % (".".join(reversed(record.address.address.split("."))),
                                                                 record.time_to_live, record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0020_aaaarecord_without_ttl(self):
        record = AAAARecord.q.filter(AAAARecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"%s IN AAAA %s" % (record.name, record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"%s.ip6.arpa. IN PTR %s" % (".".join(["%x" % ord(b) for b in reversed(
            (ipaddr.IPv6Address(record.address.address)).packed)]), record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0025_aaaarecord_with_ttl(self):
        record = AAAARecord.q.filter(AAAARecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"%s %s IN AAAA %s" % (record.name,\
                                                record.time_to_live, record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"%s.ip6.arpa. %s IN PTR %s" % (".".join(["%x" % ord(b) for b in reversed(
            (ipaddr.IPv6Address(record.address.address)).packed)]), record.time_to_live, record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0030_mxrecord(self):
        record = MXRecord.q.first()
        entry = record.gen_entry
        entry_expected = u"%s IN MX %s %s" % (record.domain, record.priority, record.server)

        self.assertEqual(entry, entry_expected)

    def test_0040_cnamerecord(self):
        record = CNameRecord.q.first()
        entry = record.gen_entry
        entry_expected = u"%s IN CNAME %s" % (record.name, record.alias_for.name)

        self.assertEqual(entry, entry_expected)

    def test_0050_nsrecord_without_ttl(self):
        record = NSRecord.q.filter(NSRecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"%s IN NS %s" % (record.domain, record.server)

        self.assertEqual(entry, entry_expected)

    def test_0055_nsrecord_with_ttl(self):
        record = NSRecord.q.filter(NSRecord.time_to_live != None).first()
        entry =  record.gen_entry
        entry_expected = u"%s %s IN NS %s" % (record.domain, record.time_to_live, record.server)

        self.assertEqual(entry, entry_expected)

    def test_0060_srvrecord_without_ttl(self):
        record = SRVRecord.q.filter(SRVRecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"%s IN SRV %s %s %s %s" % (record.service, record.priority,
                                                     record.weight, record.port, record.target)

        self.assertEqual(entry, entry_expected)

    def test_0065_srvrecord_with_ttl(self):
        record = SRVRecord.q.filter(SRVRecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"%s %s IN SRV %s %s %s %s" % (record.service, record.time_to_live,
            record.priority, record.weight, record.port, record.target)

        self.assertEqual(entry, entry_expected)
