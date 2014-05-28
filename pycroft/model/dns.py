# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import ForeignKey, Column, String, Integer
from base import ModelBase
from sqlalchemy.orm import backref, relationship, validates
import ipaddr

class Record(ModelBase):
    discriminator = Column('type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    # many to one from Record to Host
    host = relationship("Host",
        backref=backref("records", cascade="all, delete-orphan"))
    host_id = Column(Integer, ForeignKey("host.id", ondelete="CASCADE"),
        nullable=False)


class ARecord(Record):
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    name = Column(String(255), nullable=False)
    time_to_live = Column(Integer)  # optional time to live attribute

    # many to one from ARecord to Ip
    address = relationship("Ip",
        backref=backref("a_records", cascade="all, delete-orphan"))
    address_id = Column(Integer, ForeignKey("ip.id", ondelete="CASCADE"),
        nullable=False)

    __mapper_args__ = {'polymorphic_identity': 'a_record'}

    @validates('address')
    def validate_address(self, _, value):
        assert value.subnet.ip_type == "4"
        return value

    @property
    def information_human(self):
        "returns all information readable for a human"
        if self.time_to_live is not None:
            return u"%s points to %s with TTL %s" % (
                self.name, self.address.address, self.time_to_live)
        else:
            return u"%s points to %s" % (self.name, self.address.address)

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN A %s" % (self.name, self.address.address)
        else:
            return u"%s %s IN A %s" % (
                self.name, self.time_to_live, self.address.address)

    @property
    def gen_reverse_entry(self):
        reversed_address = ".".join(reversed(self.address.address.split(".")))
        if not self.time_to_live:
            return u"%s.in-addr.arpa. IN PTR %s" % (reversed_address, self.name)
        else:
            return u"%s.in-addr.arpa. %s IN PTR %s" % (
                reversed_address, self.time_to_live,
                self.name)


class AAAARecord(Record):
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    name = Column(String(255), nullable=False)
    time_to_live = Column(Integer)  # optional time to live attribute

    # many to one from ARecord to Ip
    address = relationship("Ip",
        backref=backref("aaaa_records", cascade="all, delete-orphan"))
    address_id = Column(Integer, ForeignKey("ip.id", ondelete="CASCADE"),
        nullable=False)

    __mapper_args__ = {'polymorphic_identity': 'aaaa_record'}

    @validates('address')
    def validate_address(self, _, value):
        assert value.subnet.ip_type == "6"
        return value

    @property
    def information_human(self):
        "returns all information readable for a human"
        if self.time_to_live is not None:
            return u"%s points to %s with TTL %s" % (
                self.name, self.address.address, self.time_to_live)
        else:
            return u"%s points to %s" % (self.name, self.address.address)

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN AAAA %s" % (self.name, self.address.address)
        else:
            return u"%s %s IN AAAA %s" % (
                self.name, self.time_to_live, self.address.address)

    @property
    def gen_reverse_entry(self):
        reversed_address = ".".join(["%x" % ord(b) for b in reversed(
            (ipaddr.IPv6Address(self.address.address)).packed)])
        if not self.time_to_live:
            return u"%s.ip6.arpa. IN PTR %s" % (reversed_address, self.name)
        else:
            return u"%s.ip6.arpa. %s IN PTR %s" % (
                reversed_address, self.time_to_live, self.name)


class MXRecord(Record):
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    server = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False)
    priority = Column(Integer, nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'mx_record'}

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"%s is mail-server for %s with priority %s" % (
            self.server, self.domain, self.priority)

    @property
    def gen_entry(self):
        return u"%s IN MX %s %s" % (self.domain, self.priority, self.server)


class CNAMERecord(Record):
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    name = Column(String(255), nullable=False)

    record_for_id = Column(Integer,
        ForeignKey("record.id", ondelete="CASCADE"), nullable=False)
    record_for = relationship("Record",
        primaryjoin=record_for_id == Record.id,
        backref = backref('cnames', cascade='all, delete-orphan')
    )

    __mapper_args__ = {
        'polymorphic_identity': 'cname_record',
        'inherit_condition': (id == Record.id)
    }

    @validates('record_for')
    def validate_record_for(self, _, value):
        # check if the record is of the correct type! just A record and
        # AAAA record are allowed
        assert value.discriminator == "a_record" or\
               value.discriminator == "aaaa_record"
        assert value.name != self.name

        return value

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"%s is alias for %s" % (self.name, self.record_for.name)

    @property
    def gen_entry(self):
        return u"%s IN CNAME %s" % (self.name, self.record_for.name)


class NSRecord(Record):
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    domain = Column(String(255), nullable=False)
    server = Column(String(255), nullable=False)
    time_to_live = Column(Integer)
    __mapper_args__ = {'polymorphic_identity': 'ns_record'}

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"TODO"

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN NS %s" % (self.domain, self.server)
        else:
            return u"%s %s IN NS %s" % (
                self.domain, self.time_to_live, self.server)


class SRVRecord(Record):
    id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    service = Column(String(255), nullable=False)
    time_to_live = Column(Integer)
    priority = Column(Integer, nullable=False)
    weight = Column(Integer, nullable=False)
    port = Column(Integer, nullable=False)
    target = Column(String(255), nullable=False)
    __mapper_args__ = {'polymorphic_identity': 'srv_record'}

    @property
    def information_human(self):
        "returns all information readable for a human"
        return u"TODO"

    @property
    def gen_entry(self):
        if not self.time_to_live:
            return u"%s IN SRV %s %s %s %s" % (
                self.service, self.priority, self.weight,
                self.port, self.target)
        else:
            return u"%s %s IN SRV %s %s %s %s" % (
                self.service, self.time_to_live, self.priority,
                self.weight, self.port, self.target)
