# coding: utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import (Column, Date, DateTime, Enum, Index,
                        Integer, SmallInteger, BigInteger, String, Table,
                        Text, text, ForeignKey, Boolean, Numeric)
from sqlalchemy.dialects.postgresql import INET, CIDR, MACADDR
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

import datetime

Base = declarative_base()
metadata = Base.metadata

class Account(Base):
    __tablename__ = u'accounts'

    id = Column(Integer, primary_key=True)
    login = Column(String(16), nullable=False)
    name = Column(String(64), nullable=False)
    location_id = Column(Integer, nullable=False)
    entrydate = Column(Date, nullable=False)

class Blockages(Base):
    __tablename__ = u'blockages'

    id = Column(Integer, primary_key=True)
    secure = Column(Boolean, nullable=False)
    comment = Column(String(512))
    oldshell = Column(String(64))
    account_id = Column(Integer, nullable=False)
    disabler_id = Column(Integer),
    startdate = Column(Date, nullable=False)
    days = Column(Integer, nullable=False, server_default=text("'0'"))
    expired = Column(Boolean, nullable=False, server_default="'false'")
    category_id = Column(Integer)

class Activegroups(Base):
    __tablename__ = u'activegroups'

    id = Column(Integer, primary_key=True)
    name = Column(String(16), nullable=False)
    comment = Column(String(128), nullable=False)

class Actives(Base):
    __tablename__ = u'actives'

    id = Column(Integer, primary_key=True)
    account_id  = Column(Integer, nullable=False)
    comment = Column(String(128), nullable=False)
    activegroup_id = Column(Integer, nullable=False)

class Banktransfers(Base):
    __tablename__ = u'banktransfers'

    id = Column(Integer, primary_key=True)
    agdsn_account = Column(String(32), nullable=False)
    date = Column(Date, nullable=False)
    purpose = Column(String, nullable=False)
    name =  Column(String, nullable=False)
    iban = Column(String(32), nullable=False)
    bic = Column(String(12), nullable=False)
    amount = Column(Numeric(15,2), nullable=False)
    currency = Column(String(4), nullable=False, server_default=text("'EUR'"))
    donottrytomatch = Column(Boolean, server_default=text("'false'"))


class Buildings(Base):
    __tablename__ = u'buildings'

    id = Column(Integer, primary_key=True)
    city = Column(String(32), nullable=False)
    street = Column(String(48), nullable=False)
    housenumber = Column(Integer, nullable=False)
    postcode =  Column(String(16), nullable=False)

class Floors(Base):
    __tablename__ = u'floors'

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    building_id = Column(Integer, nullable=False)

class Jacks(Base):
    __tablename__ = u'jacks'

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    port_id = Column(Integer, nullable=False)
    location_id = Column(Integer, nullable=False)
    subnet_id = Column(Integer, nullable=False)

class Locations(Base):
    __tablename__ = u'locations'

    id = Column(Integer, primary_key=True)
    room = Column(String(8))
    flat = Column(String(8))
    floor_id = Column(Integer, nullable=False)
    domain_id = Column(Integer)
    comment = Column(String(32))

class Ports(Base):
    __tablename__ = u'ports'

    id = Column(Integer, primary_key=True)
    number = Column(Integer, nullable=False)
    switch_id = Column(Integer, nullable=False)

class Switches(Base):
    __tablename__ = u'switches'

    id = Column(Integer, primary_key=True)
    ip = Column(INET, nullable=False)
    switchtype = Column(String(32), nullable=False)
    location_id = Column(Integer, nullable=False)
    comment = Column(String(64), nullable=False)

class Categories(Base):
    __tablename__ = u'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    type = Column(Integer, nullable=False)
    color = Column(String(7))
    default_text = Column(String(512))

class Domains(Base):
    __tablename__ = u'domains'

    id = Column(Integer, primary_key=True)
    name = Column(String(128), nullable=False)

class Fees(Base):
    __tablename__ = u'fees'

    id = Column(Integer, primary_key=True)
    regular = Column(Boolean, server_default=True, nullable=False)
    amount = Column(Integer, nullable=False)
    currency = Column(String(4), server_default=text("'EUR'"), nullable=False)
    description = Column(String(128), nullable=False)
    duedate = Column(Date, nullable=False)

class Financetransactions(Base):
    __tablename__ = u'financetransactions'

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, nullable=False)
    amount = Column(Numeric(15,2), nullable=False)
    currency = Column(String(4), server_default=text("'EUR'"), nullable=False)
    banktransfer_id = Column(Integer)
    fee_id = Column(Integer)

class Hostnames(Base):
    __tablename__ = u'hostnames'

    id = Column(Integer, primary_key=True)
    name = Column(String(64), nullable=False)
    domain_id = Column(Integer, nullable=False)
    primary = Column(Boolean)

class Host(Base):
    __tablename__ = u'hosts'

    id = Column(Integer, primary_key=True)
    systemhost = Column(Boolean, nullable=False)
    account_id = Column(Integer)

class Ips(Base):
    __tablename__ = u'ips'

    id = Column(Integer, primary_key=True)
    ip = Column(CIDR, nullable=False)
    mac_id = Column(Integer, nullable=False)


class Macs(Base):
    __tablename__ = u'macs'

    id = Column(Integer, primary_key=True)
    macaddr = Column(MACADDR)
    jack_id = Column(Integer)
    host_id = Column(Integer, nullable=False)

class Messages(Base):
    __tablename__ = u'messages'

    id = Column(Integer, primary_key=True)
    date = Column(Date)
    content = Column(String(512))
    account_id = Column(Integer)
    submitter_id = Column(Integer)
    category_id = Column(Integer)

class Payments(Base):
    __tablename__ = u'payments'

    id = Column(Integer, primary_key=True)
    date = Column(Date, default=datetime.datetime.utcnow, nullable=False)
    fee_id = Column(Integer, nullable=False)
    account_id = Column(Integer, nullable=False)

class Subnets(Base):
    __tablename__ = u'subnets'

    id = Column(Integer, primary_key=True)
    network = Column(INET, nullable=False)
    gateway = Column(INET, nullable=False)
    syscount = Column(Integer)

class Traffic(Base):
    __tablename__ = u'traffic'

    id = Column(CIDR, primary_key=True)
    date = Column(Date, default=datetime.datetime.utcnow, nullable=False)
    traffic_in = Column(BigInteger)
    traffic_out = Column(BigInteger)
    traffic_saved = Column(BigInteger)

class TrafficWarnedAccounts(Base):
    __tablename__ = u'traffic_warned_accounts'

    account_id = Column(Integer, primary_key=True)
