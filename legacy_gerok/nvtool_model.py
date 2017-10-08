# coding: utf-8
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Table, Text, UniqueConstraint, text
from sqlalchemy.orm import backref, relationship
from sqlalchemy.dialects.postgresql.base import CIDR, INET, MACADDR
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
metadata = Base.metadata


class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, server_default=text("nextval('accounts_id_seq'::regclass)"))
    login = Column(String(16), nullable=False, unique=True)
    name = Column(String(64), nullable=False)
    location_id = Column(ForeignKey('locations.id'), nullable=False, index=True)
    entrydate = Column(Date, nullable=False)

    location = relationship('Location')
    hosts = relationship("Host")


t_active_blockages = Table(
    'active_blockages', metadata,
    Column('id', Integer),
    Column('active', Boolean)
)


class Activegroup(Base):
    __tablename__ = 'activegroups'

    id = Column(Integer, primary_key=True, server_default=text("nextval('activegroups_id_seq'::regclass)"))
    name = Column(String(16), nullable=False)
    comment = Column(String(128), nullable=False)


class Active(Base):
    __tablename__ = 'actives'

    id = Column(Integer, primary_key=True, server_default=text("nextval('actives_id_seq'::regclass)"))
    account_id = Column(ForeignKey('accounts.id'), nullable=False, unique=True)
    comment = Column(String(128), nullable=False)
    activegroup_id = Column(ForeignKey('activegroups.id'), nullable=False, index=True)

    account = relationship('Account', uselist=False)
    activegroup = relationship('Activegroup')


class Banktransfer(Base):
    __tablename__ = 'banktransfers'
    __table_args__ = (
        Index('index_unique_transfers', 'agdsn_account', 'date', 'iban', 'bic', 'amount', 'currency'),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('banktransfers_id_seq'::regclass)"))
    agdsn_account = Column(String(32), nullable=False)
    date = Column(Date, nullable=False)
    purpose = Column(String, nullable=False)
    name = Column(String, nullable=False)
    iban = Column(String(32), nullable=False)
    bic = Column(String(12), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(4), nullable=False, server_default=text("'EUR'::character varying"))
    donottrytomatch = Column(Boolean, server_default=text("false"))


class Blockage(Base):
    __tablename__ = 'blockages'

    id = Column(Integer, primary_key=True, server_default=text("nextval('blockages_id_seq'::regclass)"))
    secure = Column(Boolean, nullable=False)
    comment = Column(String(512))
    oldshell = Column(String(64))
    account_id = Column(ForeignKey('accounts.id'), nullable=False, index=True)
    disabler_id = Column(ForeignKey('accounts.id'), index=True)
    startdate = Column(Date, nullable=False)
    days = Column(Integer, nullable=False, server_default=text("0"))
    expired = Column(Boolean, nullable=False, server_default=text("false"))
    category_id = Column(ForeignKey('categories.id'), index=True)

    account = relationship('Account', primaryjoin='Blockage.account_id == Account.id')
    category = relationship('Category')
    disabler = relationship('Account', primaryjoin='Blockage.disabler_id == Account.id')


class Building(Base):
    __tablename__ = 'buildings'

    id = Column(Integer, primary_key=True, server_default=text("nextval('buildings_id_seq'::regclass)"))
    city = Column(String(32), nullable=False)
    street = Column(String(48), nullable=False)
    housenumber = Column(Integer, nullable=False)
    postcode = Column(String(16), nullable=False)


t_cables27 = Table(
    'cables27', metadata,
    Column('switchlevel', Integer),
    Column('portnumber', Integer),
    Column('comment', String(32)),
    Column('room', String(8)),
    Column('flat', String(8)),
    Column('level', Integer),
    Column('jacknumber', Integer)
)


t_cables38 = Table(
    'cables38', metadata,
    Column('switchlevel', Integer),
    Column('portnumber', Integer),
    Column('comment', String(32)),
    Column('room', String(8)),
    Column('flat', String(8)),
    Column('level', Integer),
    Column('jacknumber', Integer)
)


class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, server_default=text("nextval('categories_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)
    type = Column(Integer, nullable=False)
    color = Column(String(7))
    default_text = Column(String(512))


class Domain(Base):
    __tablename__ = 'domains'

    id = Column(Integer, primary_key=True, server_default=text("nextval('domains_id_seq'::regclass)"))
    name = Column(String(128), nullable=False, unique=True)


class Fee(Base):
    __tablename__ = 'fees'

    id = Column(Integer, primary_key=True, server_default=text("nextval('fees_id_seq'::regclass)"))
    regular = Column(Boolean, nullable=False, server_default=text("true"))
    amount = Column(Integer, nullable=False)
    currency = Column(String(4), nullable=False, server_default=text("'EUR'::character varying"))
    description = Column(String(128), nullable=False)
    duedate = Column(Date, nullable=False)


class Financetransaction(Base):
    __tablename__ = 'financetransactions'

    id = Column(Integer, primary_key=True, server_default=text("nextval('financetransactions_id_seq'::regclass)"))
    account_id = Column(ForeignKey('accounts.id'), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(4), nullable=False, server_default=text("'EUR'::character varying"))
    banktransfer_id = Column(ForeignKey('banktransfers.id'))
    fee_id = Column(ForeignKey('fees.id'))

    account = relationship('Account')
    banktransfer = relationship('Banktransfer')
    fee = relationship('Fee')


class Floor(Base):
    __tablename__ = 'floors'

    id = Column(Integer, primary_key=True, server_default=text("nextval('floors_id_seq'::regclass)"))
    number = Column(Integer, nullable=False)
    building_id = Column(ForeignKey('buildings.id'), nullable=False, index=True)

    building = relationship('Building')


class Hostname(Base):
    __tablename__ = 'hostnames'
    __table_args__ = (
        CheckConstraint('("primary" IS NULL) OR ("primary" = true)'),
        UniqueConstraint('name', 'domain_id')
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('hostnames_id_seq'::regclass)"))
    name = Column(String(64), nullable=False)
    domain_id = Column(ForeignKey('domains.id'), nullable=False, index=True)
    primary = Column(Boolean)

    domain = relationship('Domain')
    ips = relationship('Ip', secondary='hostnames_ips')


t_hostnames_ips = Table(
    'hostnames_ips', metadata,
    Column('hostname_id', ForeignKey('hostnames.id'), primary_key=True, nullable=False),
    Column('ip_id', ForeignKey('ips.id'), primary_key=True, nullable=False),
    Index('index_hostnames_ips_on_hostname_id_and_ip_id', 'hostname_id', 'ip_id')
)


class Host(Base):
    __tablename__ = 'hosts'

    id = Column(Integer, primary_key=True, server_default=text("nextval('hosts_id_seq'::regclass)"))
    systemhost = Column(Boolean, nullable=False)
    account_id = Column(ForeignKey('accounts.id'), index=True)

    account = relationship('Account')
    mac = relationship('Mac')


class Ip(Base):
    __tablename__ = 'ips'

    id = Column(Integer, primary_key=True, server_default=text("nextval('ips_id_seq'::regclass)"))
    ip = Column(CIDR, nullable=False, unique=True)
    mac_id = Column(ForeignKey('macs.id'), nullable=False, index=True)

    mac = relationship('Mac')


class Jack(Base):
    __tablename__ = 'jacks'

    id = Column(Integer, primary_key=True, server_default=text("nextval('jacks_id_seq'::regclass)"))
    number = Column(Integer, nullable=False)
    port_id = Column(ForeignKey('ports.id'), nullable=False, unique=True)
    location_id = Column(ForeignKey('locations.id'), nullable=False, index=True)
    subnet_id = Column(ForeignKey('subnets.id'), nullable=False, index=True)

    location = relationship('Location')
    port = relationship('Port', uselist=False)
    subnet = relationship('Subnet')


t_loc27_new = Table(
    'loc27_new', metadata,
    Column('street', String(48)),
    Column('housenumber', Integer),
    Column('number', Integer),
    Column('flat', String(8)),
    Column('room', String(8)),
    Column('comment', String(32))
)


t_loc38_new = Table(
    'loc38_new', metadata,
    Column('street', String(48)),
    Column('housenumber', Integer),
    Column('number', Integer),
    Column('flat', String(8)),
    Column('room', String(8)),
    Column('comment', String(32))
)


class Location(Base):
    __tablename__ = 'locations'

    id = Column(Integer, primary_key=True, server_default=text("nextval('locations_id_seq'::regclass)"))
    room = Column(String(8))
    flat = Column(String(8))
    floor_id = Column(Integer, nullable=False, index=True)
    floor = relationship(Floor, foreign_keys=[floor_id], primaryjoin='Location.floor_id == Floor.id')
    domain_id = Column(Integer, index=True)
    comment = Column(String(32))


class Mac(Base):
    __tablename__ = 'macs'

    id = Column(Integer, primary_key=True, server_default=text("nextval('macs_id_seq'::regclass)"))
    macaddr = Column(MACADDR, unique=True)
    jack_id = Column(ForeignKey('jacks.id'), index=True)
    host_id = Column(ForeignKey('hosts.id'), nullable=False, index=True)

    host = relationship('Host')
    jack = relationship('Jack')
    ip = relationship('Ip')


class Message(Base):
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, server_default=text("nextval('messages_id_seq'::regclass)"))
    date = Column(Date)
    content = Column(String(512))
    account_id = Column(Integer, index=True)
    submitter_id = Column(Integer, index=True)
    category_id = Column(ForeignKey('categories.id'), index=True)

    category = relationship('Category')


class MydnsRr(Base):
    __tablename__ = 'mydns_rr'
    __table_args__ = (
        CheckConstraint("((type)::text = 'A'::text) OR ((type)::text = 'AAAA'::text) OR ((type)::text = 'ALIAS'::text) OR ((type)::text = 'CNAME'::text) OR ((type)::text = 'HINFO'::text) OR ((type)::text = 'MX'::text) OR ((type)::text = 'NS'::text) OR ((type)::text = 'PTR'::text) OR ((type)::text = 'RP'::text) OR ((type)::text = 'SRV'::text) OR ((type)::text = 'TXT'::text)"),
        UniqueConstraint('zone', 'name', 'type', 'data')
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval(('public.mydns_rr_id_seq'::text)::regclass)"))
    zone = Column(Integer, nullable=False)
    name = Column(String(64), nullable=False)
    type = Column(String(5), nullable=False)
    data = Column(String(128), nullable=False)
    aux = Column(Integer, nullable=False, server_default=text("0"))
    ttl = Column(Integer, nullable=False, server_default=text("86400"))
    helper_ip = Column(String(16))


class MydnsSoa(Base):
    __tablename__ = 'mydns_soa'

    id = Column(Integer, primary_key=True, server_default=text("nextval(('public.mydns_soa_id_seq'::text)::regclass)"))
    origin = Column(String(255), nullable=False, unique=True)
    ns = Column(String(255), nullable=False)
    mbox = Column(String(255), nullable=False)
    serial = Column(Integer, nullable=False, server_default=text("1"))
    refresh = Column(Integer, nullable=False, server_default=text("28800"))
    retry = Column(Integer, nullable=False, server_default=text("7200"))
    expire = Column(Integer, nullable=False, server_default=text("604800"))
    minimum = Column(Integer, nullable=False, server_default=text("86400"))
    ttl = Column(Integer, nullable=False, server_default=text("86400"))


t_mydns_sync = Table(
    'mydns_sync', metadata,
    Column('id', Integer, nullable=False),
    Column('master', String(128), server_default=text("NULL::character varying")),
    Column('type', String(6), nullable=False),
    Column('last_check', Integer)
)


class Payment(Base):
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True, server_default=text("nextval('payments_id_seq'::regclass)"))
    date = Column(Date, nullable=False, server_default=text("date(now())"))
    fee_id = Column(ForeignKey('fees.id'), nullable=False, index=True)
    account_id = Column(ForeignKey('accounts.id'), nullable=False, index=True)

    account = relationship('Account')
    fee = relationship('Fee')


class Port(Base):
    __tablename__ = 'ports'
    __table_args__ = (
        UniqueConstraint('number', 'switch_id'),
    )

    id = Column(Integer, primary_key=True, server_default=text("nextval('ports_id_seq'::regclass)"))
    number = Column(Integer, nullable=False)
    switch_id = Column(ForeignKey('switches.id'), nullable=False, index=True)

    switch = relationship('Switch')


t_radcheck = Table(
    'radcheck', metadata,
    Column('id', Integer),
    Column('username', Text),
    Column('attribute', Text),
    Column('value', Text),
    Column('op', Text)
)


t_radgroupcheck = Table(
    'radgroupcheck', metadata,
    Column('id', Integer),
    Column('groupname', Text),
    Column('attribute', Text),
    Column('value', Text),
    Column('op', Text)
)


t_radgroupreply = Table(
    'radgroupreply', metadata,
    Column('priority', Integer),
    Column('groupname', String(64)),
    Column('attribute', String(64)),
    Column('op', String(2)),
    Column('value', String(253))
)


t_radpostauth = Table(
    'radpostauth', metadata,
    Column('id', BigInteger, nullable=False, server_default=text("nextval('radpostauth_id_seq'::regclass)")),
    Column('username', String(253), nullable=False),
    Column('nasipaddress', INET, nullable=False),
    Column('nasportid', String(15), nullable=False),
    Column('packettype', String(32)),
    Column('replymessage', String(253)),
    Column('authdate', DateTime, nullable=False, server_default=text("timezone('utc'::text, now())"))
)


t_radreply = Table(
    'radreply', metadata,
    Column('id', Integer),
    Column('username', Text),
    Column('attribute', Text),
    Column('value', Text),
    Column('op', Text)
)


t_radusergroup = Table(
    'radusergroup', metadata,
    Column('groupname', Text),
    Column('username', Text),
    Column('priority', Integer)
)


t_schema_migrations = Table(
    'schema_migrations', metadata,
    Column('version', String(255), nullable=False, unique=True)
)


class Subnet(Base):
    __tablename__ = 'subnets'

    id = Column(Integer, primary_key=True, server_default=text("nextval('subnets_id_seq'::regclass)"))
    gateway = Column(INET, nullable=False)
    network = Column(INET, nullable=False)
    syscount = Column(Integer)


t_sw = Table(
    'sw', metadata,
    Column('ip', INET),
    Column('type', String(32)),
    Column('number', Integer),
    Column('comment', String(32)),
    Column('housenumber', Integer)
)


class Switch(Base):
    __tablename__ = 'switches'

    id = Column(Integer, primary_key=True, server_default=text("nextval('switches_id_seq'::regclass)"))
    ip = Column(INET, nullable=False, unique=True)
    switchtype = Column(String(32), nullable=False)
    location_id = Column(ForeignKey('locations.id'), nullable=False, index=True)
    comment = Column(String(64), nullable=False)

    location = relationship('Location')


t_traffic = Table(
    'traffic', metadata,
    Column('ip', CIDR, nullable=False),
    Column('date', Date, nullable=False, server_default=text("date(now())")),
    Column('traffic_in', BigInteger),
    Column('traffic_out', BigInteger),
    Column('traffic_saved', BigInteger),
    UniqueConstraint('ip', 'date'),
    Index('index_traffic_on_ip_and_date', 'ip', 'date', unique=True)
)


t_traffic_warned_accounts = Table(
    'traffic_warned_accounts', metadata,
    Column('account_id', ForeignKey('accounts.id'), nullable=False, unique=True)
)
