# Copyright (c) 2013 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy.types import Integer
from sqlalchemy import ForeignKey, Column

from pycroft.lib.host_alias import delete_alias, change_alias, create_arecord, \
    create_cnamerecord, create_aaaarecord, create_mxrecord, create_nsrecord, \
    create_srvrecord, _create_alias
from pycroft.model.host import Ip, UserHost
from pycroft.model import session
from pycroft.model.host_alias import ARecord, AAAARecord, MXRecord, CNameRecord, \
    NSRecord, SRVRecord, HostAlias
from tests.lib.fixtures.host_alias_fixtures import ARecordData, AAAARecordData, \
    NSRecordData, CNameRecordData, MXRecordData, SRVRecordData, IpData, UserHostData
from tests import FixtureDataTestBase


class Test_010_RemovingOFAlias(FixtureDataTestBase):
    datasets = [ARecordData, AAAARecordData, NSRecordData, CNameRecordData,
                MXRecordData, SRVRecordData]

    def test_0010_arecord(self):
        record = ARecord.q.first()
        delete_alias(record.id)

        self.assertIsNone(ARecord.q.filter(ARecord.id == record.id).first())

    def test_0020_aaaarecord(self):
        record = AAAARecord.q.first()
        delete_alias(record.id)

        self.assertIsNone(
            AAAARecord.q.filter(AAAARecord.id == record.id).first())

    def test_0030_nsrecord(self):
        record = NSRecord.q.first()
        delete_alias(record.id)

        self.assertIsNone(NSRecord.q.filter(NSRecord.id == record.id).first())

    def test_0040_cnamerecord(self):
        record = CNameRecord.q.first()
        delete_alias(record.id)

        self.assertIsNone(
            CNameRecord.q.filter(CNameRecord.id == record.id).first())

    def test_0050_mxrecord(self):
        record = MXRecord.q.first()
        delete_alias(record.id)

        self.assertIsNone(MXRecord.q.filter(MXRecord.id == record.id).first())

    def test_0060_srvrecord(self):
        record = SRVRecord.q.first()
        delete_alias(record.id)

        self.assertIsNone(SRVRecord.q.filter(SRVRecord.id == record.id).first())

    def test_0070_wrong_id(self):
        aliases = HostAlias.q.all()

        self.assertRaises(ValueError, delete_alias, len(aliases) + 10)


class Test_020_ChangingOfAlias(FixtureDataTestBase):
    datasets = [CNameRecordData]

    def test_0010_correct_attribute(self):
        record = CNameRecord.q.first()

        change_alias(record, name="correct_attribute")

        self.assertEqual(
            CNameRecord.q.filter(CNameRecord.id == record.id).one().name,
            "correct_attribute")

    def test_0020_wrong_attribute(self):
        record = CNameRecord.q.first()

        self.assertRaises(ValueError, change_alias, alias=record,
                          test="wrong_attribute")


class Test_030_CreatingOfAlias(FixtureDataTestBase):
    datasets = [ARecordData, AAAARecordData, NSRecordData, CNameRecordData,
                MXRecordData, SRVRecordData, IpData]

    def test_0010_arecord_without_ttl(self):
        address = Ip.q.filter(Ip.id == IpData.ip_v4.id).one()
        host = UserHost.q.first()
        name = "test"

        record = create_arecord(address_id=address.id, name=name,
                                host_id=host.id)

        self.assertEqual(ARecord.q.filter(ARecord.id == record.id).one().name,
                         name)
        self.assertEqual(
            ARecord.q.filter(ARecord.id == record.id).one().address,
            address)
        self.assertIsNone(
            ARecord.q.filter(ARecord.id == record.id).one().time_to_live)
        self.assertEqual(ARecord.q.filter(ARecord.id == record.id).one().host,
                         host)

        delete_alias(record.id)

    def test_0015_arecord_with_ttl(self):
        address = Ip.q.filter(Ip.id == IpData.ip_v4.id).one()
        host = UserHost.q.first()
        name = "test"
        ttl = 100

        record = create_arecord(address_id=address.id, name=name,
                                time_to_live=ttl, host_id=host.id)

        self.assertEqual(ARecord.q.filter(ARecord.id == record.id).one().name,
                         name)
        self.assertEqual(
            ARecord.q.filter(ARecord.id == record.id).one().address,
            address)
        self.assertEqual(
            ARecord.q.filter(ARecord.id == record.id).one().time_to_live,
            ttl)
        self.assertEqual(ARecord.q.filter(ARecord.id == record.id).one().host,
                         host)

        delete_alias(record.id)

    def test_0020_aaaarecord_without_ttl(self):
        address = Ip.q.filter(Ip.id == IpData.ip_v6.id).one()
        host = UserHost.q.first()
        name = "test"

        record = create_aaaarecord(address_id=address.id, name=name,
                                   host_id=host.id)

        self.assertEqual(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().name,
            name)
        self.assertEqual(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().address,
            address)
        self.assertIsNone(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().time_to_live)
        self.assertEqual(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().host,
            host)

        delete_alias(record.id)

    def test_0025_aaaarecord_with_ttl(self):
        address = Ip.q.filter(Ip.id == IpData.ip_v6.id).one()
        host = UserHost.q.first()
        name = "test"
        ttl = 100

        record = create_aaaarecord(address_id=address.id, name=name,
                                   time_to_live=ttl, host_id=host.id)

        self.assertEqual(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().name,
            name)
        self.assertEqual(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().address,
            address)
        self.assertEqual(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().time_to_live,
            ttl)
        self.assertEqual(
            AAAARecord.q.filter(AAAARecord.id == record.id).one().host,
            host)

        delete_alias(record.id)

    def test_0030_cnamerecord(self):
        alias_for = ARecord.q.first()
        host = UserHost.q.first()
        name = "test"

        record = create_cnamerecord(alias_for_id=alias_for.id, name=name,
                                    host_id=host.id)

        self.assertEqual(
            CNameRecord.q.filter(CNameRecord.id == record.id).one().alias_for,
            alias_for)
        self.assertEqual(
            CNameRecord.q.filter(CNameRecord.id == record.id).one().name,
            name)
        self.assertEqual(
            CNameRecord.q.filter(CNameRecord.id == record.id).one().host,
            host)

        delete_alias(record.id)

    def test_0040_mxrecord(self):
        host = UserHost.q.first()
        server = "server"
        domain = "domain"
        priority = 10

        record = create_mxrecord(priority=priority, server=server,
                                 domain=domain, host_id=host.id)

        self.assertEqual(
            MXRecord.q.filter(MXRecord.id == record.id).one().server,
            server)
        self.assertEqual(
            MXRecord.q.filter(MXRecord.id == record.id).one().domain,
            domain)
        self.assertEqual(
            MXRecord.q.filter(MXRecord.id == record.id).one().priority,
            priority)
        self.assertEqual(MXRecord.q.filter(MXRecord.id == record.id).one().host,
                         host)

        delete_alias(record.id)

    def test_0050_nsrecord_without_ttl(self):
        host = UserHost.q.first()
        domain = "domain"
        server = "server"

        record = create_nsrecord(domain=domain, server=server,
                                 host_id=host.id)

        self.assertEqual(
            NSRecord.q.filter(NSRecord.id == record.id).one().domain,
            domain)
        self.assertEqual(
            NSRecord.q.filter(NSRecord.id == record.id).one().server,
            server)
        self.assertIsNone(
            NSRecord.q.filter(NSRecord.id == record.id).one().time_to_live)
        self.assertEqual(NSRecord.q.filter(NSRecord.id == record.id).one().host,
                         host)

        delete_alias(record.id)

    def test_0055_nsrecord_with_ttl(self):
        host = UserHost.q.first()
        domain = "domain"
        server = "server"
        ttl = 10

        record = create_nsrecord(domain=domain, server=server,
                                 time_to_live=ttl, host_id=host.id)

        self.assertEqual(
            NSRecord.q.filter(NSRecord.id == record.id).one().domain,
            domain)
        self.assertEqual(
            NSRecord.q.filter(NSRecord.id == record.id).one().server,
            server)
        self.assertEqual(
            NSRecord.q.filter(NSRecord.id == record.id).one().time_to_live, ttl)
        self.assertEqual(NSRecord.q.filter(NSRecord.id == record.id).one().host,
                         host)

        delete_alias(record.id)

    def test_0060_srvrecord_without_ttl(self):
        host = UserHost.q.first()
        service = "service"
        priority = 10
        weight = 100
        port = 1010
        target = "target"

        record = create_srvrecord(priority=priority, service=service,
                                  weight=weight, port=port, target=target,
                                  host_id=host.id)

        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().service,
            service)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().priority,
            priority)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().weight,
            weight)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().port,
            port)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().target,
            target)
        self.assertIsNone(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().time_to_live)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().host,
            host)

        delete_alias(record.id)

    def test_0065_srvrecord_without_ttl(self):
        host = UserHost.q.first()
        service = "service"
        priority = 10
        weight = 100
        port = 1010
        ttl = 10000
        target = "target"

        record = create_srvrecord(priority=priority, service=service,
                                  weight=weight, port=port, target=target,
                                  time_to_live=ttl,
                                  host_id=host.id)

        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().service,
            service)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().priority,
            priority)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().weight,
            weight)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().port,
            port)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().target,
            target)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().time_to_live,
            ttl)
        self.assertEqual(
            SRVRecord.q.filter(SRVRecord.id == record.id).one().host,
            host)

        delete_alias(record.id)


class Test_040_MalformedTypes(FixtureDataTestBase):
    datasets = [UserHostData]

    class MalformedRecord(HostAlias):
        id = Column(Integer, ForeignKey("hostalias.id"), primary_key=True)
        __mapper_args__ = {'polymorphic_identity': 'malformedrecord'}

    def test_0010_create_malformed_record(self):
        self.assertRaises(ValueError, _create_alias, 'malformedrecord')

    def test_0020_delete_malformed_record(self):
        alias = Test_040_MalformedTypes.MalformedRecord(
            host=UserHost.q.first())
        session.session.add(alias)
        session.session.commit()

        self.assertRaises(ValueError, delete_alias, alias.id)

        session.session.delete(alias)
        session.session.commit()
