# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import inspect

import ipaddr

from pycroft.model.dns import Record, ARecord, AAAARecord, MXRecord, \
    CNAMERecord, NSRecord, SRVRecord
from pycroft.model.host import Ip, UserHost
from pycroft.model import session
from tests import FixtureDataTestBase
from tests.fixtures.dummy.dns import (
    ARecordData, AAAARecordData, MXRecordData, CNAMERecordData, NSRecordData,
    SRVRecordData)
from tests.fixtures.dummy.host import IpData, UserHostData


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
        entry_expected = u"{} {} IN AAAA {}".format(record.name,
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
        a_record = ARecord.q.filter_by(
            name=ARecordData.without_ttl.name, time_to_live=None).one()
        c_names = a_record.cnames
        session.session.delete(a_record)
        session.session.commit()
        self.assertTrue(all(inspect(r).deleted for r in c_names))

    def test_0030_cname_on_aaaa_record_delete(self):
        aaaa_record = AAAARecord.q.filter_by(
            name=AAAARecordData.without_ttl.name, time_to_live=None).one()
        c_names = aaaa_record.cnames
        session.session.delete(aaaa_record)
        session.session.commit()
        self.assertTrue(all(inspect(r).deleted for r in c_names))

    def test_0040_a_record_on_ip_delete(self):
        ip = Ip.q.filter_by(address=IpData.dummy_user_ipv4.address).one()
        a_records = ip.a_records
        session.session.delete(ip)
        session.session.commit()
        self.assertTrue(all(inspect(r).deleted for r in a_records))

    def test_0045_aaaa_record_on_ip_delete(self):
        ip = Ip.q.filter_by(address=IpData.dummy_user_ipv6.address).one()
        aaaa_records = ip.aaaa_records
        session.session.delete(ip)
        session.session.commit()
        self.assertTrue(all(inspect(r).deleted for r in aaaa_records))
