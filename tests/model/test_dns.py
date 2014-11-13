# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from tests.model.fixtures.dns_fixtures import ARecordData, AAAARecordData,\
    MXRecordData, CNAMERecordData, NSRecordData, SRVRecordData, IpData, UserHostData
from pycroft.model.dns import Record, ARecord, AAAARecord, MXRecord, \
    CNAMERecord, NSRecord, SRVRecord
from tests import FixtureDataTestBase
from pycroft.model.host import      Ip, UserHost
from pycroft.model import session
import ipaddr

class Test_010_ARecordValidator(FixtureDataTestBase):
    datasets = [ARecordData, IpData]

    def test_0010_ip_validate(self):
        record = ARecord.q.first()

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
        record = AAAARecord.q.first()

        def set_ip(ip):
            record.address = ip

        ips = Ip.q.all()

        for ip in ips:
            if ip.subnet.ip_type == "4":
                self.assertRaises(AssertionError, set_ip, ip)
                break


class Test_025_CNAMERecordValidator(FixtureDataTestBase):
    datasets = [ARecordData, MXRecordData, UserHostData]

    def test_0010_record_for_name_validator(self):
        a_record = ARecord.q.first()
        host = UserHost.q.first()

        self.assertRaises(AssertionError, CNAMERecord, name=a_record.name,
            record_for=a_record, host_id=host.id)

        new_record = CNAMERecord(name=a_record.name + "_test",
            record_for=a_record, host_id=host.id)

    def test_0020_record_for_type_validator(self):
        mx_record = MXRecord.q.first()
        host = UserHost.q.first()

        self.assertRaises(AssertionError, CNAMERecord, name="test",
            record_for=mx_record, host_id=host.id)


class Test_030_GenEntryMethods(FixtureDataTestBase):
    datasets = [ARecordData, AAAARecordData, MXRecordData, CNAMERecordData,
                NSRecordData, SRVRecordData]

    def test_0010_a_record_without_ttl(self):
        record = ARecord.q.filter(ARecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"{} IN A {}".format(record.name, record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"{}.in-addr.arpa. IN PTR {}".format(
            ".".join(reversed(record.address.address.split("."))), record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0015_a_record_with_ttl(self):
        record = ARecord.q.filter(ARecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"{} {} IN A {}".format(
            record.name, record.time_to_live, record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"{}.in-addr.arpa. {} IN PTR {}".format(
            ".".join(reversed(record.address.address.split("."))),
            record.time_to_live, record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0020_aaaa_record_without_ttl(self):
        record = AAAARecord.q.filter(AAAARecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"{} IN AAAA {}".format(
            record.name, record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"{}.ip6.arpa. IN PTR {}".format(
            ".".join(["{:x}".format(ord(b)) for b in reversed(
                (ipaddr.IPv6Address(record.address.address)).packed)]),
            record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0025_aaaa_record_with_ttl(self):
        record = AAAARecord.q.filter(AAAARecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"{} {} IN AAAA {}".format(record.name,\
                                                record.time_to_live,
                                                record.address.address)

        self.assertEqual(entry, entry_expected)

        rev_entry = record.gen_reverse_entry
        rev_entry_expected = u"{}.ip6.arpa. {} IN PTR {}".format(
            ".".join(["{:x}".format(ord(b)) for b in reversed(
                (ipaddr.IPv6Address(record.address.address)).packed)]),
            record.time_to_live, record.name)

        self.assertEqual(rev_entry, rev_entry_expected)

    def test_0030_mx_record(self):
        record = MXRecord.q.first()
        entry = record.gen_entry
        entry_expected = u"{} IN MX {} {}".format(
            record.domain, record.priority, record.server)

        self.assertEqual(entry, entry_expected)

    def test_0040_cname_record(self):
        record = CNAMERecord.q.first()
        entry = record.gen_entry
        entry_expected = u"{} IN CNAME {}".format(
            record.name, record.record_for.name)

        self.assertEqual(entry, entry_expected)

    def test_0050_ns_record_without_ttl(self):
        record = NSRecord.q.filter(NSRecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"{} IN NS {}".format(record.domain, record.server)

        self.assertEqual(entry, entry_expected)

    def test_0055_ns_record_with_ttl(self):
        record = NSRecord.q.filter(NSRecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"{} {} IN NS {}".format(
            record.domain, record.time_to_live, record.server)

        self.assertEqual(entry, entry_expected)

    def test_0060_srv_record_without_ttl(self):
        record = SRVRecord.q.filter(SRVRecord.time_to_live == None).first()
        entry = record.gen_entry
        entry_expected = u"{} IN SRV {} {} {} {}".format(
            record.service, record.priority,
            record.weight, record.port, record.target)

        self.assertEqual(entry, entry_expected)

    def test_0065_srv_record_with_ttl(self):
        record = SRVRecord.q.filter(SRVRecord.time_to_live != None).first()
        entry = record.gen_entry
        entry_expected = u"{} {} IN SRV {} {} {} {}".format(
            record.service, record.time_to_live,
            record.priority, record.weight, record.port, record.target)

        self.assertEqual(entry, entry_expected)


class Test_040_Cascades(FixtureDataTestBase):
    datasets = [ARecordData, AAAARecordData, MXRecordData, CNAMERecordData,
                NSRecordData, SRVRecordData, UserHostData, IpData]

    def test_0010_record_on_host_delete(self):
        for host in UserHost.q.all():
            session.session.delete(host)

        session.session.commit()
        # assert that all records to the host are gone
        self.assertIsNone(Record.q.first())
        self.assertIsNone(ARecord.q.first())
        self.assertIsNone(AAAARecord.q.first())
        self.assertIsNone(CNAMERecord.q.first())
        self.assertIsNone(MXRecord.q.first())
        self.assertIsNone(SRVRecord.q.first())
        self.assertIsNone(NSRecord.q.first())


    def test_0020_cname_on_a_record_delete(self):
        for record in ARecord.q.all():
            session.session.delete(record)

        session.session.commit()

        self.assertIsNone(CNAMERecord.q.filter(
            CNAMERecord.id == CNAMERecordData.dummy_record.id).first())


    def test_0030_cname_on_aaaa_record_delete(self):
        for record in AAAARecord.q.all():
            session.session.delete(record)

        session.session.commit()

        self.assertIsNone(CNAMERecord.q.filter(
            CNAMERecord.id == CNAMERecordData.dummy_record2.id).first())


    def test_0040_a_record_on_ip_delete(self):
        ip = Ip.q.filter(Ip.id == IpData.ip_v4.id).first()
        a_record_id = ARecord.q.filter(ARecord.address == ip).first().id
        session.session.delete(ip)

        session.session.commit()

        self.assertIsNone(ARecord.q.get(a_record_id))

    def test_0045_aaaa_record_on_ip_delete(self):
        ip = Ip.q.filter(Ip.id == IpData.ip_v6.id).first()
        aaaa_record_id = AAAARecord.q.filter(AAAARecord.address == ip).first().id
        session.session.delete(ip)

        session.session.commit()

        self.assertIsNone(AAAARecord.q.get(aaaa_record_id))
