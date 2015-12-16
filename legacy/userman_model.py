# coding: utf-8
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Table, Text, text
from sqlalchemy.dialects.postgresql import INET

#only sqlalchemy >=0.9 knows OID
try:
    from sqlalchemy.dialects.postgresql import OID
except ImportError:
    print "No OID type, using Integer"
    OID = Integer

from sqlalchemy.orm import relationship
from sqlalchemy.schema import CheckConstraint
from sqlalchemy.types import NullType
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
metadata = Base.metadata


class Anschluss(Base):
    __tablename__ = u'anschluss'

    anschluss_id = Column(Integer, primary_key=True, server_default=text("nextval(('anschluss_id_seq'::text)::regclass)"))
    uid = Column(Integer, nullable=False)
    subnetz_id = Column(ForeignKey(u'subnetz.subnetz_id'), nullable=False)
    anmeldedatum = Column(Date, nullable=False, server_default=text("now()"))
    zimmer_id = Column(Integer, nullable=False)
    ip = Column(INET, unique=True)
    hostname = Column(String(16))
    os = Column(String(16))
    typ = Column(String(16))
    bes = Column(Text)

    subnetz = relationship(u'Subnetz')


t_anschluss_alle = Table(
    u'anschluss_alle', metadata,
    Column(u'anschluss_id', Integer),
    Column(u'uid', Integer),
    Column(u'subnetz_id', Integer),
    Column(u'anmeldedatum', Date),
    Column(u'sperrdatum', Date),
    Column(u'ip', INET),
    Column(u'hostname', String(16)),
    Column(u'os', String),
    Column(u'typ', String),
    Column(u'bes', Text)
)


class AnschlussAlt(Base):
    __tablename__ = u'anschluss_alt'

    anschluss_id = Column(Integer, primary_key=True, server_default=text("nextval(('anschluss_id_seq'::text)::regclass)"))
    uid = Column(Integer, nullable=False)
    anmeldedatum = Column(Date, nullable=False)
    sperrdatum = Column(Date, nullable=False, server_default=text("now()"))
    zimmer_id = Column(Integer)
    ip = Column(INET)
    hostname = Column(String(16))
    bes = Column(Text)


class FinanzKonten(Base):
    __tablename__ = u'finanz_konten'

    id = Column(u"konto_id", Integer, primary_key=True, server_default=text("nextval(('konto_id_seq'::text)::regclass)"))
    name = Column(String(40), nullable=False)
    description = Column(u"bes", Text)
    type = Column(u"konto_typ", ForeignKey(u'finanz_konto_typ.konto_typ_id'), nullable=False)
    nutzer_bezogen = Column(Boolean, nullable=False, server_default=text("false"))
    abgeschlossen = Column(Boolean, nullable=False, server_default=text("false"))

    finanz_konto_typ = relationship(u'FinanzKontoTyp')

    # Adjacency list: see http://docs.sqlalchemy.org/en/rel_0_8/orm/relationships.html?highlight=adjacency%20list#configuring-self-referential-eager-loading
    parent_konto_id = Column(u"vater_konto", ForeignKey(u'finanz_konten.konto_id'))
    children = relationship(u'FinanzKonten', remote_side=[id], backref=u"vater_konto", lazy="joined", join_depth=2)


class FinanzBuchungen(Base):
    __tablename__ = u'finanz_buchungen'

    fbid = Column(Integer, primary_key=True, server_default=text("nextval(('fbid_seq'::text)::regclass)"))
    datum = Column(Date, nullable=False, server_default=text("('now'::text)::date"))
    bearbeiter = Column(String, nullable=False, server_default=text("\"current_user\"()"))
    rechnungs_nr = Column(Integer)
    wert = Column(Integer, nullable=False, server_default=text("0"))
    soll = Column(ForeignKey(FinanzKonten.id), nullable=False)
    soll_uid = Column(Integer)
    soll_konto = relationship(FinanzKonten, backref="soll_fb", foreign_keys=[soll])
    haben = Column(ForeignKey(FinanzKonten.id), nullable=False)
    haben_uid = Column(Integer)
    haben_konto = relationship(FinanzKonten, backref="haben_fb", foreign_keys=[haben])

    bes = Column(Text)


class FinanzGruppe(Base):
    __tablename__ = u'finanz_gruppe'

    fgid = Column(Integer, primary_key=True, server_default=text("nextval(('fgid_seq'::text)::regclass)"))
    name = Column(String(40), nullable=False)
    semester = Column(Integer, nullable=False, server_default=text("0"))
    anschluss = Column(Integer, nullable=False, server_default=text("0"))
    zw_semester = Column(Integer, nullable=False, server_default=text("0"))
    zw_anschluss = Column(Integer, nullable=False, server_default=text("0"))


class FinanzKontoTyp(Base):
    __tablename__ = u'finanz_konto_typ'

    konto_typ_id = Column(String(8), primary_key=True)
    name = Column(String(40), nullable=False)
    bes = Column(Text)


class BankKonto(Base):
    """Bankkontobewegungen"""
    __tablename__ = u'bank_konto'

    bkid = Column(Integer, primary_key=True, server_default=text("nextval(('\"bank_konto_bkid_seq\"'::text)::regclass)"))
    valid_on = Column(u'datum', Date, nullable=False)
    wert = Column(Integer, nullable=False, server_default=text("0"))
    bes = Column(Text)


class BkBuchung(BankKonto):
    """Verbuchte Bankkontobewegungen"""
    __tablename__ = u'bk_buchung'

    bkid = Column(ForeignKey(BankKonto.bkid), primary_key=True)
    posted_at = Column(u'datum', DateTime(True), nullable=False, server_default=text("now()"))
    bearbeiter = Column(String, nullable=False, server_default=text("\"current_user\"()"))
    rechnungs_nr = Column(Integer)
    konto_id = Column(ForeignKey(FinanzKonten.id), nullable=False)
    konto = relationship(FinanzKonten, backref="bankbuchungen")
    uid = Column(Integer)


class Buchungen(Base):
    __tablename__ = u'buchungen'

    oid = Column(OID, primary_key=True)
    bkid = Column(Integer)
    fbid = Column(Integer)
    datum = Column(Date)
    bearbeiter = Column(String)
    rechnungs_nr = Column(Integer)
    soll = Column(ForeignKey(FinanzKonten.id))
    soll_uid = Column(Integer)
    soll_konto = relationship(FinanzKonten, backref="soll_buchungen", foreign_keys=[soll])
    haben = Column(ForeignKey(FinanzKonten.id))
    haben_konto = relationship(FinanzKonten, backref="haben_buchungen", foreign_keys=[haben])
    relationship(FinanzKonten)
    haben_uid = Column(Integer)
    wert = Column(Integer)
    bes = Column(Text)

    __table_args__ = (
            CheckConstraint('NOT(soll IS NULL AND haben IS NULL)'),
            )


class Cname(Base):
    __tablename__ = u'cname'

    cname = Column(String(16), primary_key=True, nullable=False)
    subnetz_id = Column(ForeignKey(u'subnetz.subnetz_id'), primary_key=True, nullable=False)
    anschluss_id = Column(ForeignKey(u'anschluss.anschluss_id'), nullable=False)

    anschluss = relationship(u'Anschluss')
    subnetz = relationship(u'Subnetz')


class Gruppe(Base):
    __tablename__ = u'gruppe'

    gid = Column(Integer, primary_key=True, server_default=text("nextval(('gid_id_seq'::text)::regclass)"))
    name = Column(String(40), nullable=False)
    bes = Column(Text)
    ip = Column(Boolean, nullable=False, server_default=text("true"))
    account = Column(Boolean, nullable=False, server_default=text("true"))
    semester = Column(Integer, nullable=False, server_default=text("0"))
    anschluss = Column(Integer, nullable=False, server_default=text("0"))
    zw_semester = Column(Integer, nullable=False, server_default=text("0"))
    zw_anschluss = Column(Integer, nullable=False, server_default=text("0"))


class Hp4108Port(Base):
    __tablename__ = u'hp4108_ports'

    id = Column(Integer, primary_key=True, server_default=text("nextval(('\"hp4108_ports_id_seq\"'::text)::regclass)"))
    etage = Column(String(10))
    zimmernr = Column(String(10))
    port = Column(String(10))
    haus = Column(String(10))
    ip = Column(String(20))
    sperrbar = Column(String(1))
    kommentar = Column(String(30))


class Log(Base):
    __tablename__ = u'log'

    log_id = Column(Integer, primary_key=True, server_default=text("nextval(('log_id_seq'::text)::regclass)"))
    uid = Column(Integer)
    anschluss_id = Column(ForeignKey(u'anschluss.anschluss_id'))
    autor = Column(String(16), nullable=False, server_default=text("\"current_user\"()"))
    log_typ_id = Column(ForeignKey(u'log_typ.log_typ_id'), nullable=False)
    meta = Column("metadata", String(40))
    zeit = Column(DateTime, nullable=False, server_default=text("('now'::text)::timestamp(6) with time zone"))
    notifed = Column(Integer, nullable=False, server_default=text("0"))
    bes = Column(Text, nullable=False)

    anschluss = relationship(u'Anschluss')
    log_typ = relationship(u'LogTyp')


class LogTyp(Base):
    __tablename__ = u'log_typ'

    log_typ_id = Column(String(32), primary_key=True)
    level = Column(Integer, nullable=False, server_default=text("3"))
    verfall_typ = Column(String(1), nullable=False, server_default=text("'A'::bpchar"))
    geschuetzt = Column(Boolean, nullable=False, server_default=text("false"))
    verfall_zeit = Column(Integer)
    email_notify = Column(Boolean, server_default=text("false"))
    email = Column(String(60))
    name = Column(String(40))
    bes = Column(Text)


t_mac = Table(
    u'mac', metadata,
    Column(u'anschluss_id', ForeignKey(u'anschluss.anschluss_id'), nullable=False),
    Column(u'mac', String(17))
)


class Mailalia(Base):
    __tablename__ = u'mailalias'

    alias_id = Column(Integer, primary_key=True, server_default=text("nextval(('mailalias_id_seq'::text)::regclass)"))
    email = Column(String(20), nullable=False, unique=True)
    uid = Column(Integer, nullable=False)


t_mailinglist_addon = Table(
    u'mailinglist_addon', metadata,
    Column(u'maillist_id', ForeignKey(u'mailinglisten.maillist_id'), nullable=False),
    Column(u'email', String(40), nullable=False)
)


class Mailinglisten(Base):
    __tablename__ = u'mailinglisten'

    maillist_id = Column(Integer, primary_key=True, server_default=text("nextval(('maillist_id_seq'::text)::regclass)"))
    name = Column(String(40), nullable=False)
    datei = Column(String(40))
    email = Column(String(40), nullable=False, unique=True)


t_mailinglisten_map = Table(
    u'mailinglisten_map', metadata,
    Column(u'maillist_id', ForeignKey(u'mailinglisten.maillist_id'), nullable=False),
    Column(u'gid', Integer, nullable=False)
)


class MapNutzerGruppe(Base):
    __tablename__ = u'map_nutzer_gruppe'
    __table_args__ = (
        Index(u'gid_uid', u'gid', u'uid', unique=True),
        Index(u'uid_gid', u'uid', u'gid', unique=True)
    )

    uid = Column(Integer, primary_key=True, nullable=False)
    gid = Column(Integer, primary_key=True, nullable=False)
    datum = Column(Date, nullable=False, server_default=text("now()"))
    verfallsdatum = Column(Date)


class MapNutzerStatu(Base):
    __tablename__ = u'map_nutzer_status'

    map_nutzer_status_id = Column(Integer, primary_key=True, server_default=text("nextval(('map_nutzer_status_seq'::text)::regclass)"))
    uid = Column(Integer, nullable=False)
    status_id = Column(ForeignKey(u'status.status_id'), nullable=False)
    datum = Column(Date, nullable=False, server_default=text("now()"))
    verfallsdatum = Column(Date)
    bes = Column(Text)

    status = relationship(u'Statu')


t_map_wheim_subnetz = Table(
    u'map_wheim_subnetz', metadata,
    Column(u'wheim_id', ForeignKey(u'wheim.wheim_id'), nullable=False),
    Column(u'subnetz_id', ForeignKey(u'subnetz.subnetz_id'), nullable=False),
    Column(u'prio', Integer, nullable=False)
)


class Nutzer(Base):
    __tablename__ = u'nutzer'

    uid = Column(Integer, primary_key=True, server_default=text("nextval(('uid_seq'::text)::regclass)"))
    name = Column(String(40), nullable=False)
    vname = Column(String(40), nullable=False)
    email = Column(String(40))
    geburtsdatum = Column(Date)
    geburtsort = Column(String(40))
    geburtsland = Column(String(40))
    tel = Column(String(40))
    unix_account = Column(String(24), unique=True)
    zimmer_id = Column(Integer)
    adresse = Column(String(40))
    plz = Column(String(12))
    ort = Column(String(40))
    anmeldedatum = Column(Date, nullable=False, server_default=text("now()"))
    last_changed = Column(Date, server_default=text("now()"))
    last_gid_change = Column(Date, server_default=text("now()"))
    bes = Column(Text)
    gid = Column(ForeignKey(u'gruppe.gid'), nullable=False)
    quota_id = Column(ForeignKey(u'quota.quota_id'), nullable=False)
    traffic_id = Column(ForeignKey(u'traffic.traffic_id'), nullable=False)

    gruppe = relationship(u'Gruppe')
    quota = relationship(u'Quota')
    traffic = relationship(u'Traffic')


t_nutzer_buchungen = Table(
    u'nutzer_buchungen', metadata,
    Column(u'oid', OID, primary_key=True),
    Column(u'bkid', Integer),
    Column(u'fbid', Integer),
    Column(u'datum', Date),
    Column(u'bearbeiter', String),
    Column(u'rechnungs_nr', Integer),
    Column(u'soll', Integer),
    Column(u'soll_uid', Integer),
    Column(u'haben', Integer),
    Column(u'haben_uid', Integer),
    Column(u'wert', Integer),
    Column(u'bes', Text)
)


t_nutzer_konto_uebersicht = Table(
    u'nutzer_konto_uebersicht', metadata,
    Column(u'uid', Integer),
    Column(u'name', String(40)),
    Column(u'vname', String(40)),
    Column(u'gid', Integer),
    Column(u'gruppen_name', String(40)),
    Column(u'wert', BigInteger),
    Column(u'tage', Integer)
)


class NutzerPasswd(Base):
    __tablename__ = u'nutzer_passwd'

    uid = Column(Integer, primary_key=True)
    md5pass = Column(String(32))
    krbpass = Column(String(32))
    authmd5pass = Column(String(32))


class Quota(Base):
    __tablename__ = u'quota'

    quota_id = Column(Integer, primary_key=True, server_default=text("nextval(('quota_id_seq'::text)::regclass)"))
    byte_h = Column(Integer)
    byte_s = Column(Integer)
    files_h = Column(Integer)
    files_s = Column(Integer)
    name = Column(String(16), nullable=False)
    bes = Column(Text)


class Statu(Base):
    __tablename__ = u'status'

    status_id = Column(Integer, primary_key=True, server_default=text("nextval(('status_id_seq'::text)::regclass)"))
    name = Column(String(40), nullable=False)
    internet = Column(Boolean, nullable=False, server_default=text("true"))
    login = Column(Boolean, nullable=False, server_default=text("true"))


class Subnetz(Base):
    __tablename__ = u'subnetz'

    subnetz_id = Column(Integer, primary_key=True, server_default=text("nextval(('subnetz_id_seq'::text)::regclass)"))
    name = Column(String(16), nullable=False)
    ip = Column(String(15))
    bcast = Column(String(15))
    gw = Column(String(15))
    mask = Column(String(15))
    reserviert = Column(Integer)
    domain = Column(String(64))
    vlan = Column(String(16))
    bes = Column(Text)


t_temp = Table(
    u'temp', metadata,
    Column(u'log_typ_id', String(8)),
    Column(u'level', Integer),
    Column(u'verfall_typ', String(1)),
    Column(u'geschuetzt', Boolean),
    Column(u'verfall_zeit', Integer),
    Column(u'email_notify', Boolean),
    Column(u'email', String(60)),
    Column(u'name', String(40)),
    Column(u'bes', Text)
)


class Traffic(Base):
    __tablename__ = u'traffic'

    traffic_id = Column(Integer, primary_key=True, server_default=text("nextval(('traffic_id_seq'::text)::regclass)"))
    input = Column(BigInteger, server_default=text("0"))
    output = Column(BigInteger, server_default=text("0"))
    total = Column(BigInteger, server_default=text("0"))
    fall_back = Column(Integer)
    verfallsdatum = Column(Date)
    name = Column(String(16), nullable=False)
    bes = Column(Text)


class TrafficTuext(Base):
    __tablename__ = u'traffic_tuext'
    __table_args__ = (
        Index(u'traffic_tuext_index', u'ip', u'timetag', unique=True),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval(('traffic_tuext_id_seq'::text)::regclass)"))
    input = Column(BigInteger, server_default=text("0"))
    output = Column(BigInteger, server_default=text("0"))
    timetag = Column(Integer, nullable=False)
    ip = Column(INET, nullable=False)


t_view_anschluss_alle = Table(
    u'view_anschluss_alle', metadata,
    Column(u'anschluss_id', Integer),
    Column(u'uid', Integer),
    Column(u'subnetz_id', Integer),
    Column(u'anmeldedatum', Date),
    Column(u'sperrdatum', Date),
    Column(u'ip', INET),
    Column(u'hostname', String(16)),
    Column(u'os', String),
    Column(u'typ', String),
    Column(u'bes', Text),
    Column(u'zimmer_id', Integer)
)


t_view_ip_traffic = Table(
    u'view_ip_traffic', metadata,
    Column(u'uid', Integer),
    Column(u'name', String(40)),
    Column(u'vname', String(40)),
    Column(u'unix_account', String(24)),
    Column(u'input', Numeric),
    Column(u'output', Numeric),
    Column(u'total', Numeric),
    Column(u'ip', INET),
    Column(u'quota', NullType),
    Column(u'traffic', String(16))
)


t_view_nutzer_traffic = Table(
    u'view_nutzer_traffic', metadata,
    Column(u'uid', Integer),
    Column(u'name', String(40)),
    Column(u'vname', String(40)),
    Column(u'unix_account', String(24)),
    Column(u'input', Numeric),
    Column(u'output', Numeric),
    Column(u'total', Numeric),
    Column(u'ip', NullType),
    Column(u'quota', Numeric),
    Column(u'traffic', String(16))
)


class Wheim(Base):
    __tablename__ = u'wheim'

    wheim_id = Column(Integer, primary_key=True, server_default=text("nextval(('wheim_id_seq'::text)::regclass)"))
    krzl = Column(String(6), nullable=False)
    adresse = Column(String(40), nullable=False)
    ort = Column(String(40), nullable=False, server_default=text("'Dresden'::character varying"))
    plz = Column(String(12), nullable=False, server_default=text("'D-01217'::character varying"))


class Zimmer(Base):
    __tablename__ = u'zimmer'

    zimmer_id = Column(Integer, primary_key=True, server_default=text("nextval(('\"zimmer_zimmer_id_seq\"'::text)::regclass)"))
    wheim_id = Column(Integer)
    etage = Column(String(10))
    name = Column(String(10))
    bedient_durch = Column(String(20))
    port = Column(String(10))

