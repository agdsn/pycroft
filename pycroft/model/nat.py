from sqlalchemy import CheckConstraint, Column, ForeignKey, \
    Integer, SmallInteger, String, Text, \
    UniqueConstraint, func, and_, ForeignKeyConstraint
from sqlalchemy.orm import relationship, backref, remote, foreign

from pycroft.model.base import IntegerIdModel, ModelBase
from pycroft.model.types import IPAddress, MACAddress, IPNetwork
from pycroft.model.user import User


def single_ipv4_constraint(col: Column):
    return CheckConstraint(and_(func.family(col) == 4, func.masklen(col) == 32))


class NATDomain(IntegerIdModel):
    name = Column(String, nullable=False)


def nat_domain_fkey():
    return ForeignKey(NATDomain.id, ondelete="CASCADE", onupdate="CASCADE")


class DHCPHostReservation(ModelBase):
    nat_domain_id = Column(Integer, nat_domain_fkey(),
                           primary_key=True, nullable=False)
    nat_domain = relationship(NATDomain)

    ip = Column(IPAddress, primary_key=True, nullable=False)
    mac = Column(MACAddress, nullable=False)

    __table_args__ = (
        single_ipv4_constraint(col=ip),
    )


class InsideNetwork(ModelBase):
    nat_domain_id = Column(Integer, nat_domain_fkey(),
                           primary_key=True, nullable=False)
    nat_domain = relationship(NATDomain)

    ip_network = Column(IPNetwork, primary_key=True, nullable=False)
    gateway = Column(IPAddress, nullable=False)


class OutsideIPAddress(ModelBase):
    nat_domain_id = Column(Integer, nat_domain_fkey(),
                           primary_key=True, nullable=False)
    nat_domain = relationship(NATDomain)

    ip_address = Column(IPAddress, primary_key=True, nullable=False)
    owner_id = Column(Integer, ForeignKey(User.id))
    owner = relationship(User, backref="outside_ip_addresses")

    __table_args__ = (
        single_ipv4_constraint(col=ip_address),
    )


class Translation(ModelBase):
    nat_domain_id = Column(Integer, primary_key=True, nullable=False)
    # careful: we don't have a FKey to NATDomain, only to OutsideIPAddress.
    # therefore, `relationship(NATDomain)` does not quite work.
    nat_domain = relationship(
        NATDomain,
        primaryjoin=(remote(NATDomain.id) == foreign(nat_domain_id))
    )

    outside_address = Column(IPAddress, primary_key=True, nullable=False)
    inside_network = Column(IPNetwork, nullable=False)
    owner = relationship(User,
                         secondary=OutsideIPAddress.__table__,
                         backref="translations")

    __table_args__ = (
        single_ipv4_constraint(col=outside_address),
        ForeignKeyConstraint(
            (nat_domain_id, outside_address),
            (OutsideIPAddress.nat_domain_id, OutsideIPAddress.ip_address),
            ondelete="CASCADE", onupdate="CASCADE"
        ),
    )


class Forwarding(ModelBase):
    nat_domain_id = Column(Integer, nat_domain_fkey(),
                           nullable=False)
    nat_domain = relationship(NATDomain)

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

    __mapper_args__ = {
        'primary_key': (nat_domain_id, outside_address, protocol, outside_port),
    }

    __table_args__ = (
        UniqueConstraint(nat_domain_id, outside_address, protocol, outside_port),
    )
