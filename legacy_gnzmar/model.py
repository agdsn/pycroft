# coding: utf-8
from sqlalchemy import BigInteger, Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import INET, MACADDR
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class PatchRoom(Base):
    __tablename__ = 'patch_room'

    patchport = Column(String, primary_key=True)
    room = Column(String, primary_key=True)
    switchroom = Column(String, primary_key=True)
    building = Column(String, primary_key=True)


class SwitchPatch(Base):
    __tablename__ = 'switch_patch'

    switchname = Column(String, primary_key=True)
    switchport = Column(String, primary_key=True)
    patchport = Column(String, primary_key=True)


class MAC(Base):
    __tablename__ = 'mac'

    id = Column(Integer, primary_key=True)
    router = Column(String, primary_key=False)
    intNr = Column(Integer, primary_key=False)
    interface = Column(String, primary_key=False)
    mac = Column(MACADDR, primary_key=False)
    time = Column(String, primary_key=False)
    last_seen = Column(String, primary_key=False)
