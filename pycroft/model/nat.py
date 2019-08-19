from sqlalchemy import CheckConstraint, Column, ForeignKey, \
    ForeignKeyConstraint, Integer, SmallInteger, String, Table, Text, \
    UniqueConstraint, text, func, and_
from sqlalchemy.orm import relationship, backref

from pycroft.model.base import IntegerIdModel, ModelBase
from pycroft.model.net import Subnet
from pycroft.model.types import IPAddress, MACAddress
from pycroft.model.user import User


class NATDomain(IntegerIdModel):
    name = Column(String, nullable=False)


class DHCPHostReservation(ModelBase):
    nat_domain_id = Column(ForeignKey(NATDomain.id), primary_key=True,
                           nullable=False)
    nat_domain = relationship(NATDomain)

    ip = Column(IPAddress, primary_key=True, nullable=False)
    mac = Column(MACAddress, nullable=False)

    __table_args__ = (
        CheckConstraint(and_(func.family(ip) == 4, func.masklen(ip) == 32)),
    )


class InsideNetwork(ModelBase):
    nat_domain_id = Column(ForeignKey(NATDomain.id), primary_key=True,
                           nullable=False)
    nat_domain = relationship(NATDomain)

    ip_network = Column(Subnet, primary_key=True, nullable=False)
    gateway = Column(IPAddress, nullable=False)

    __table_args__ = (
        CheckConstraint(''),
        CheckConstraint('')
    )


class OutsideIPAddress(ModelBase):
    nat_domain_id = Column(ForeignKey(NATDomain.id), primary_key=True,
                           nullable=False)
    nat_domain = relationship(NATDomain)

    ip_address = Column(IPAddress, primary_key=True, nullable=False)
    owner = Column(Integer)

    __table_args__ = (
        CheckConstraint(
            '(family(ip_address) = 4) AND (masklen(ip_address) = 32)'),
    )


class Translation(ModelBase):
    nat_domain_id = Column(ForeignKey(NATDomain.id), primary_key=True,
                           nullable=False)
    nat_domain = relationship(NATDomain)

    outside_address = Column(IPAddress, primary_key=True, nullable=False)
    inside_network = Column(Subnet, nullable=False)

    owner_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                      nullable=False)
    owner = relationship(User, backref=backref("translations",
                                               cascade="all, delete-orphan"))

    __table_args__ = (
        CheckConstraint(and_(func.family(ip) == 4, func.masklen(ip) == 32)),
    )


class Forwarding(ModelBase):
    nat_domain_id = Column(ForeignKey(NATDomain.id, ondelete="CASCADE"),
                           primary_key=True,
                           nullable=False)
    nat_domain = relationship(NATDomain, backref=backref("forwardings",
                                                         cascade="all, delete-orphan"))

    outside_address = Column(IPAddress, nullable=False)
    outside_port = Column(Integer)

    inside_address = Column(IPAddress, nullable=False)
    inside_port = Column(Integer)

    protocol = Column(SmallInteger, nullable=False)

    comment = Column(Text)

    owner_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                      nullable=False)
    owner = relationship(User, backref=backref("forwardings",
                                               cascade="all, delete-orphan"))

    __table_args__ = (
        UniqueConstraint(nat_domain, outside_address, protocol, outside_port)
    )
