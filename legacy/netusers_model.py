# coding: utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import (Column, Date, DateTime, Enum, Index,
                        Integer, SmallInteger, String, Table,
                        Text, text, ForeignKey, func)
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Status(Base):
    __tablename__ = u'status'

    id = Column(Integer, primary_key=True, server_default=text("'0'"))
    short_str = Column(String(30), nullable=False, server_default=text("''"))
    long_str = Column(String(60), nullable=False, server_default=text("''"))
    account = Column(Enum(u'Y', u'N', name="tmp1"), nullable=False, server_default=text("'Y'"))
    ip = Column(Enum(u'Y', u'N', name="tmp2"), nullable=False, server_default=text("'Y'"))
    del_account = Column(Enum(u'Y', u'N', name="tmp3"), nullable=False, server_default=text("'Y'"))
    dns = Column(Enum(u'Y', u'N', name="tmp4"), nullable=False, server_default=text("'Y'"))


class Nutzer(Base):
    __tablename__ = u'nutzer'
    __table_args__ = (
        Index(u'zimmer', u'etage', u'zimmernr'),
    )

    nutzer_id = Column(Integer, primary_key=True, server_default=text("'0'"))
    name = Column(String(30), nullable=False, server_default=text("''"))
    vname = Column(String(30), nullable=False, server_default=text("''"))
    wheim_id = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    etage = Column(Integer, nullable=False, server_default=text("'0'"))
    raw_zimmernr = Column('zimmernr', String(10), nullable=False, server_default=text("''"))
    @hybrid_property
    def zimmernr(self):
        return self.raw_zimmernr.upper()

    @zimmernr.expression
    def zimmernr(self):
        return func.upper(self.raw_zimmernr)

    tel = Column(String(20))
    unix_account = Column(String(40), nullable=False, unique=True)
    anmeldedatum = Column(Date, nullable=False, server_default=text("'1970-01-01'"))
    sperrdatum = Column(Date)
    status_id = Column(u"status", ForeignKey(Status.id), nullable=False, index=True, server_default=text("'1'"))
    comment = Column(Text)
    last_change = Column(DateTime, nullable=False, server_default=text("'1970-01-01'"))
    icq_uin = Column(String(255))
    bezahlt = Column(SmallInteger, nullable=False, server_default=text("'1'"))
    internet_by_rental = Column(SmallInteger, nullable=False, server_default=text("'0'"))
    use_cache = Column(SmallInteger, nullable=False, server_default=text("'0'"))

    computer = relationship("Computer", backref="nutzer")
    status = relationship(Status, lazy='joined')


class Computer(Base):
    __tablename__ = u'computer'

    computer_id = Column(Integer, primary_key=True)

    nutzer_id = Column(Integer, ForeignKey(Nutzer.nutzer_id), nullable=False)

    c_wheim_id = Column(Integer, nullable=False, server_default=text("'0'"))
    c_etage = Column(Integer)
    c_zimmernr = Column(String(10))
    raw_zimmernr = Column('c_zimmernr', String(10))

    @hybrid_property
    def c_zimmernr(self):
        try:
            return self.raw_zimmernr.upper()
        except AttributeError:
            return self.raw_zimmernr

    @c_zimmernr.expression
    def c_zimmernr(self):
        return func.upper(self.raw_zimmernr)

    c_typ = Column(String(20))
    c_cpu = Column(String(10))
    c_bs = Column(String(20))
    c_etheraddr = Column(String(20))
    c_ip = Column(INET, nullable=False, index=True)
    c_hname = Column(String(20), nullable=False, server_default=text("''"))
    c_alias = Column(String(20))
    c_subnet_id = Column(Integer, nullable=False, server_default=text("'0'"))
    c_eth_segment = Column(String(20))
    mgmt_ip = Column(INET, nullable=True)
    last_change = Column(DateTime, nullable=False, server_default=text("'1970-01-01'"))


class Credit(Base):
    __tablename__ = u'credit'

    user_id = Column(Integer, primary_key=True, nullable=False)
    amount = Column(Integer, primary_key=True, nullable=False)
    timetag = Column(Integer, primary_key=True, nullable=False)


class Hp4108Port(Base):
    __tablename__ = u'hp4108_ports'
    __table_args__ = (
        Index(u'zimmer_idx', u'zimmernr', u'etage'),
    )

    id = Column(Integer, primary_key=True)
    port = Column(String(10))
    haus = Column(String(10))

    wheim_id = Column(Integer, nullable=False, index=True, server_default=text("'0'"))
    etage = Column(String(10))
    zimmernr = Column(String(10))
    raw_zimmernr = Column('zimmernr', String(10))

    @hybrid_property
    def zimmernr(self):
        try:
            return self.raw_zimmernr.upper()
        except AttributeError:
            return self.raw_zimmernr

    @zimmernr.expression
    def zimmernr(self):
        return func.upper(self.raw_zimmernr)

    ip = Column(INET)

    sperrbar = Column(String(1))
    kommentar = Column(String(50))

class Kabel(Base):
    __tablename__ = u'kabel'

    wheim_id = Column(Integer, primary_key=True, nullable=False, server_default=text("'0'"))
    etage = Column(Integer, primary_key=True, nullable=False, server_default=text("'0'"))
    zimmernr = Column(String(10), primary_key=True, nullable=False, server_default=text("''"))
    last_change = Column(DateTime, nullable=False, server_default=text("'1970-01-01'"))


class NewAccount(Base):
    __tablename__ = u'new_accounts'

    nutzer_id = Column(Integer, primary_key=True, server_default=text("'0'"))
    Password = Column(String(8), nullable=False, server_default=text("''"))
    last_change = Column(DateTime, nullable=False, server_default=text("'1970-01-01'"))
    email = Column(String(50), nullable=False, server_default=text("''"))


class Subnet(Base):
    __tablename__ = u'subnet'

    subnet_id = Column(Integer, nullable=False, primary_key=True, index=True, server_default=text("'0'"))
    domain = Column(String(30), nullable=False, server_default=text("''"))
    net_ip = Column(String(15), nullable=False, server_default=text("''"))
    netmask = Column(String(15), nullable=False, server_default=text("''"))
    net_broadcast = Column(String(15), nullable=False, server_default=text("''"))
    default_gateway = Column(String(15), nullable=False, server_default=text("''"))
    vlan_name = Column(String(15))


t_versionen = Table(
    u'versionen', metadata,
    Column(u'program', String(10), nullable=False, server_default=text("''")),
    Column(u'dbase', Integer),
    Column(u'major', Integer),
    Column(u'minor', Integer)
)


class Wheim(Base):
    __tablename__ = u'wheim'

    wheim_id = Column(Integer, nullable=False, primary_key=True, index=True, server_default=text("'0'"))
    kuerzel = Column(String(8), nullable=False, server_default=text("''"))
    str = Column(String(30), nullable=False, server_default=text("''"))
    hausnr = Column(String(4))
    stadt = Column(String(20), nullable=False, server_default=text("''"))
    plz = Column(String(5), nullable=False, server_default=text("''"))


class ZihIncident(Base):
    __tablename__ = u'zih_incidents'

    id = Column(String(30), primary_key=True)
    type = Column(String(255), nullable=False)
    ip = Column(String(15), nullable=False)
    time = Column(DateTime, nullable=False)
