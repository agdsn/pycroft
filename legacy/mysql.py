from sqlalchemy import MetaData, create_engine, Table, Column
from sqlalchemy.orm import sessionmaker, scoped_session, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.expression import ColumnCollection
from sqlalchemy.types import Integer


def get_passwd(filename):
    pw = ""
    with open(filename, "r") as f:
        pw = f.read()
    return pw


class ReprMixin(object):
    def __repr__(self):
        args = ", ".join("%s='%s'" % (
        key, getattr(self, key)) for key in self.__table__.columns.keys())
        return u"%s(%s)" % (self.__class__.__name__, args)


Base = declarative_base(cls=ReprMixin)
engine = create_engine('mysql://%s@127.0.0.1/netusers' % get_passwd("mysql_pw"))
meta = MetaData(bind=engine)
session = None


class Wheim(Base):
    props = ColumnCollection(Column('wheim_id', Integer, primary_key=True))
    __table__ = Table('wheim', meta, *props, autoload=True)

    def port_qry(self):
        return session.query(Hp4108Ports).filter(
            Hp4108Ports.haus == self.kuerzel).order_by(Hp4108Ports.etage,
            Hp4108Ports.zimmernr)


class Hp4108Ports(Base):
    __table__ = Table('hp4108_ports', meta, autoload=True)


class Nutzer(Base):
    __table__ = Table('nutzer', meta, autoload=True)


class Computer(Base):
    __table__ = Table('computer', meta, autoload=True)


class Subnet(Base):
    props = ColumnCollection(Column('subnet_id', Integer, primary_key=True))
    __table__ = Table('subnet', meta, *props, autoload=True)


class Status(Base):
    __table__ = Table('status', meta, autoload=True)


session = scoped_session(sessionmaker(bind=engine))