# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from itertools import chain, imap
import operator
from sqlalchemy import (
    ForeignKey, Column, String, Integer, UniqueConstraint, event)
from sqlalchemy.orm import backref, relationship
from pycroft.model.base import ModelBase
from pycroft.model.host import IP


class DNSZone(ModelBase):
    name = Column(String(255), nullable=False)

    def export(self):
        return u"\n".join(chain(
            (u"$ORIGIN {0}".format(self.name),),
            imap(operator.methodcaller("export"), self.records)))


class DNSName(ModelBase):
    name = Column(String(255), nullable=False)
    zone_id = Column(Integer, ForeignKey(DNSZone.id), nullable=False)
    zone = relationship(DNSZone, lazy=False,
                        backref=backref("names", cascade="all, delete-orphan",
                                        order_by=name))
    __table_args__ = (
        UniqueConstraint(zone_id, name),
    )

    @property
    def fqdn(self):
        if self.name == u'@':
            return u"{0}.".format(self.zone.name)
        return u"{0}.{1}.".format(self.name, self.zone.name)


class Record(ModelBase):
    discriminator = Column('type', String(50))
    record_type = None

    name_id = Column(Integer, ForeignKey(DNSName.id, ondelete="CASCADE"),
                     nullable=False)
    name = relationship(DNSName, lazy=False,
                        backref=backref("records", passive_deletes=True,
                                        cascade="all, delete-orphan"))
    zone = relationship(DNSZone, backref=backref("records", viewonly=True),
                        secondary=DNSName.__table__, viewonly=True)
    ttl = Column(Integer)
    __mapper_args__ = {'polymorphic_on': discriminator}

    def export(self):
        if self.ttl:
            return u"{} {} IN {} {}".format(
                self.name.name, self.ttl, self.record_type, self.record_data)
        else:
            return u"{} IN {} {}".format(self.name.name, self.record_type,
                                         self.record_data)

    @property
    def record_data(self):
        raise NotImplementedError()


class AddressRecord(Record):
    id = Column(Integer, ForeignKey('record.id', ondelete="CASCADE"),
                primary_key=True)
    address_id = Column(Integer, ForeignKey(IP.id, ondelete="CASCADE"),
                        nullable=False)
    address = relationship(IP, lazy=False,
                           backref=backref("address_records",
                                           passive_deletes=True,
                                           cascade="all, delete-orphan"))

    __mapper_args__ = {'polymorphic_identity': 'address_record'}

    @property
    def record_type(self):
        return 'A' if self.address.address.version == '4' else 'AAAA'

    @property
    def record_data(self):
        return self.address.address


class CNAMERecord(Record):
    id = Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"),
                primary_key=True)
    record_type = 'CNAME'
    cname_id = Column(Integer,
                      ForeignKey(DNSName.id, ondelete="CASCADE"),
                      nullable=False)
    cname = relationship(DNSName, foreign_keys=[cname_id], lazy=False)
    __mapper_args__ = {'polymorphic_identity': 'cname_record'}

    @property
    def record_data(self):
        return self.cname.fqdn


class MXRecord(Record):
    id = Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"),
                primary_key=True)
    record_type = 'MX'
    preference = Column(Integer, nullable=False)
    exchange_id = Column(Integer, ForeignKey(DNSName.id), nullable=False)
    exchange = relationship(DNSName, foreign_keys=[exchange_id], lazy=False)
    __mapper_args__ = {'polymorphic_identity': 'mx_record'}

    @property
    def record_data(self):
        return u"{} {}".format(self.preference, self.exchange.fqdn)


class NSRecord(Record):
    id = Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"),
                primary_key=True)
    record_type = 'NS'
    nsdname_id = Column(Integer, ForeignKey(DNSName.id),
                        nullable=False)
    nsdname = relationship(DNSName, foreign_keys=[nsdname_id], lazy=False)
    __mapper_args__ = {'polymorphic_identity': 'ns_record'}

    @property
    def record_data(self):
        return self.nsdname.fqdn


class PTRRecord(Record):
    id = Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"),
                primary_key=True)
    record_type = 'PTR'
    address_id = Column(Integer, ForeignKey(IP.id, ondelete="CASCADE"),
                        nullable=False, unique=True)
    address = relationship(IP, backref=backref("ptr_record", uselist=False,
                                               passive_deletes=True,
                                               cascade="all, delete-orphan"))
    ptrdname_id = Column(Integer, ForeignKey(DNSName.id, ondelete="CASCADE"),
                         nullable=False)
    ptrdname = relationship(DNSName, foreign_keys=[ptrdname_id], lazy=False)
    __mapper_args__ = {'polymorphic_identity': 'ptr_record'}

    @property
    def record_data(self):
        return self.ptrdname.fqdn


class SOARecord(Record):
    id = Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"),
                primary_key=True)

    record_type = 'SOA'
    mname_id = Column(Integer, ForeignKey(DNSName.id, ondelete="CASCADE"),
                      nullable=False)
    mname = relationship(DNSName, foreign_keys=[mname_id], lazy=False)
    rname = Column(String(255), nullable=False)
    serial = Column(Integer, nullable=False)
    refresh = Column(Integer, nullable=False)
    retry = Column(Integer, nullable=False)
    expire = Column(Integer, nullable=False)
    minimum = Column(Integer, nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'soa_record'}

    @property
    def record_data(self):
        return u"{0} {1} ({2:d} {3:d} {4:d} {5:d} {6:d})".format(
            self.mname.fqdn, self.rname, self.serial, self.refresh, self.retry,
            self.expire, self.minimum)


class SRVRecord(Record):
    id = Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"),
                primary_key=True)
    record_type = 'SRV'
    priority = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=False)
    port = Column(Integer, nullable=False)
    target_id = Column(Integer, ForeignKey(DNSName.id, ondelete="CASCADE"),
                       nullable=False)
    target = relationship(DNSName, foreign_keys=[target_id], lazy=False)
    __mapper_args__ = {'polymorphic_identity': 'srv_record'}

    @property
    def record_data(self):
        return u"{0:d} {1:d} {2:d} {3}".format(self.priority, self.weight,
                                               self.port, self.target.fqdn)


class TXTRecord(Record):
    id = Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"),
                primary_key=True)
    record_type = 'TXT'
    txt_data = Column(String(255), nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'txt_record'}

    @property
    def record_data(self):
        return self.txt_data


def _cname_exclusive(mapper, connection, target):
    records = target.name.records
    has_cname = any(imap(lambda r: isinstance(r, CNAMERecord), records))
    if has_cname and len(records) > 1:
        raise ValueError("Domain name {0} has a CNAME record, it must not "
                         "have any other resource "
                         "records.".format(target.name.name))


for record_type in (AddressRecord, CNAMERecord, MXRecord, NSRecord, PTRRecord,
                    SOARecord, SRVRecord, TXTRecord):
    event.listen(AddressRecord, "before_insert", _cname_exclusive)
    event.listen(AddressRecord, "before_update", _cname_exclusive)
