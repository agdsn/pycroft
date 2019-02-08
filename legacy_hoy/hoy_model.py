# coding: utf-8
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import INET, MACADDR
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Config(Base):
    __tablename__ = 'config'

    config_name = Column(String(64), primary_key=True)
    config_value = Column(Text, nullable=False)


class Room(Base):
    __tablename__ = 'rooms'

    rid = Column(Integer, primary_key=True, server_default=text("nextval('rooms_rid_seq'::regclass)"))
    house = Column(Integer, server_default=text("10"))
    etage = Column(Integer)
    room = Column(Integer, index=True)
    annex = Column(String(3))
    default_net = Column(Integer, nullable=False)
    default_ip = Column(Integer, nullable=False)
    room_desc = Column(String(32))


class User(Base):
    __tablename__ = 'users'
    __table_args__ = (
        CheckConstraint('(closed_until_date IS NULL) OR (closed_until_percent IS NULL)'),
        CheckConstraint('online_from < online_to'),
        CheckConstraint('traffic_percent_1 < traffic_percent_2')
    )

    uid = Column(Integer, primary_key=True, server_default=text("nextval('users_uid_seq'::regclass)"))
    rid = Column(ForeignKey('rooms.rid'), nullable=False)
    netid = Column(Integer, nullable=False, server_default=text("1"))
    firstname = Column(String(45), nullable=False)
    lastname = Column(String(45), nullable=False)
    email = Column(String(63), nullable=False)
    online_from = Column(Date, nullable=False)
    online_to = Column(Date, nullable=False, server_default=text("'9999-12-31'::date"))
    in_mailv = Column(Boolean, nullable=False, server_default=text("true"))
    traffic_mail_1 = Column(Boolean, server_default=text("false"))
    traffic_mail_2 = Column(Boolean, server_default=text("false"))
    traffic_closed_count = Column(Integer, nullable=False, server_default=text("0"))
    temp_closed = Column(Boolean, nullable=False, server_default=text("false"))
    traffic_percent_1 = Column(Integer, nullable=False, server_default=text("80"))
    traffic_percent_2 = Column(Integer, nullable=False, server_default=text("95"))
    traffic_max = Column(BigInteger)
    close_method = Column(Integer, nullable=False, server_default=text("1"))
    closed_until_date = Column(DateTime)
    closed_until_percent = Column(Integer)
    port_id = Column(ForeignKey('ports.id'), nullable=False)
    ftp = Column(Boolean, nullable=False, server_default=text("false"))
    netdevice = Column(ForeignKey('netdevice.netdev_id'), nullable=False, server_default=text("14"))
    cable = Column(Boolean, nullable=False, server_default=text("false"))
    mycomment = Column(Text, nullable=False, server_default=text("''::text"))

    room = relationship('Room')


class Ip(Base):
    __tablename__ = 'ips'
    __table_args__ = (
        UniqueConstraint('ip', 'ip_id'),
    )

    ip_id = Column(Integer, primary_key=True, server_default=text("nextval('ips_ip_id_seq'::regclass)"))
    uid = Column(ForeignKey('users.uid'))
    ip = Column(INET, nullable=False)
    mac = Column(MACADDR)
    net_id = Column(ForeignKey('netconfig.net_id'), nullable=False, server_default=text("0"))
    port_id = Column(ForeignKey('ports.id'), nullable=False)
    device_id = Column(Integer, nullable=False)
    hostname = Column(String(12), nullable=False)
    mycomment = Column(Text)

    user = relationship('User')
