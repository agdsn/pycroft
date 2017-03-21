# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import chain
import operator
from sqlalchemy import inspect

from pycroft._compat import imap
from pycroft.model.dns import (
    AddressRecord, DNSZone, CNAMERecord, MXRecord, NSRecord, SOARecord,
    SRVRecord, TXTRecord, record_types)
from pycroft.model.host import IP, UserHost
from pycroft.model import session
from tests import FixtureDataTestBase
from tests.fixtures.dummy.dns_records import (
    AddressRecordData, MXRecordData, CNAMERecordData, NSRecordData,
    SOARecordData, SRVRecordData, TXTRecordData)
from tests.fixtures.dummy.dns_zones import DNSZoneData
from tests.fixtures.dummy.host import IPData, UserHostData
from tests.fixtures.dummy.net import SubnetData


class TestZoneGeneration(FixtureDataTestBase):
    datasets = (AddressRecordData, MXRecordData, CNAMERecordData, NSRecordData,
                SOARecordData, SRVRecordData, TXTRecordData, SubnetData)

    def assertRecordExportCorrect(self, record):
        record.ttl = None
        expected = u"{} IN {} {}".format(
            record.name.name, record.record_type, record.record_data)
        self.assertEqual(expected, record.export())
        record.ttl = 1000
        expected = u"{} {} IN {} {}".format(
            record.name.name, record.ttl, record.record_type,
            record.record_data)
        self.assertEqual(expected, record.export())

    def test_address_record(self):
        for record in AddressRecord.q:
            self.assertEqual(record.record_data, record.address.address)
            self.assertRecordExportCorrect(record)

    def test_mx_record(self):
        record = MXRecord.q.first()
        expected = u"{} {}".format(record.preference, record.exchange.fqdn)
        self.assertEqual(record.record_data, expected)
        self.assertRecordExportCorrect(record)

    def test_cname_record(self):
        record = CNAMERecord.q.first()
        self.assertEqual(record.record_data, record.cname.fqdn)
        self.assertRecordExportCorrect(record)

    def test_ns_record(self):
        record = NSRecord.q.filter_by().first()
        self.assertEqual(record.record_data, record.nsdname.fqdn)
        self.assertRecordExportCorrect(record)

    def test_soa_record(self):
        record = SOARecord.q.filter_by().first()
        expected = u"{0} {1} ({2:d} {3:d} {4:d} {5:d} {6:d})".format(
            record.mname.fqdn, record.rname, record.serial, record.refresh,
            record.retry, record.expire, record.minimum)
        self.assertEqual(record.record_data, expected)
        self.assertRecordExportCorrect(record)

    def test_srv_record(self):
        record = SRVRecord.q.filter_by().first()
        expected = u"{0:d} {1:d} {2:d} {3}".format(
            record.priority, record.weight, record.port, record.target.fqdn)
        self.assertEqual(record.record_data, expected)
        self.assertRecordExportCorrect(record)

    def test_txt_record(self):
        record = TXTRecord.q.filter_by().first()
        self.assertEqual(record.record_data, record.txt_data)
        self.assertRecordExportCorrect(record)

    def test_zone_export(self):
        zone = DNSZone.q.filter_by(name=DNSZoneData.example_com.name).one()
        records = chain(*(
            session.session.query(record_type)
            .join(record_type.zone).filter(DNSZone.id == zone.id)
            for record_type in record_types))
        records = sorted(records, key=operator.attrgetter("name"))
        expected = u"\n".join(chain((u"$ORIGIN {0}".format(zone.name),),
                                    imap(operator.methodcaller("export"),
                                         records)))
        self.assertEqual(zone.export(), expected)


class TestCascades(FixtureDataTestBase):
    datasets = (AddressRecordData, MXRecordData, CNAMERecordData, NSRecordData,
                SRVRecordData, UserHostData, IPData)

    def test_record_on_host_delete(self):
        address_records = []
        for host in UserHost.q.all():
            for ip in host.ips:
                address_records.extend(ip.address_records)
            session.session.delete(host)
        session.session.commit()
        self.assertTrue(all(inspect(o).deleted for o in address_records))

    def test_0040_address_record_on_ipv4_delete(self):
        ip = IP.q.filter_by(address=IPData.dummy_user_ipv4.address).one()
        records = ip.address_records
        session.session.delete(ip)
        session.session.commit()
        self.assertTrue(all(inspect(r).deleted for r in records))

    def test_0045_address_record_on_ipv6_delete(self):
        ip = IP.q.filter_by(address=IPData.dummy_user_ipv6.address).one()
        address_records = ip.address_records
        session.session.delete(ip)
        session.session.commit()
        self.assertTrue(all(inspect(r).deleted for r in address_records))
