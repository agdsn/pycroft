# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, CheckConstraint, PrimaryKeyConstraint
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import Insert
from sqlalchemy.types import BigInteger, Enum, Integer, DateTime

from pycroft.model.base import ModelBase, IntegerIdModel
from pycroft.model.ddl import DDLManager, Rule
from pycroft.model.types import IPAddress
from pycroft.model.user import User
from pycroft.model.functions import utcnow
from pycroft.model.host import IP


ddl = DDLManager()


class TrafficBalance(ModelBase):
    user_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                     primary_key=True)
    user = relationship(User,
                        backref=backref("_traffic_balance", uselist=False))
    amount = Column(BigInteger, nullable=False)
    timestamp = Column(DateTime, default=utcnow(), nullable=False)


class TrafficEvent(object):
    timestamp = Column(DateTime, default=utcnow(), nullable=False)
    amount = Column(BigInteger, CheckConstraint('amount >= 0'),
                    nullable=False)


class TrafficVolume(TrafficEvent, IntegerIdModel):
    type = Column(Enum("Ingress", "Egress", name="traffic_direction"),
                  nullable=False)
    ip_id = Column(Integer, ForeignKey(IP.id, ondelete="CASCADE"),
                   nullable=False)
    ip = relationship(IP, backref=backref("traffic_volumes",
                                          cascade="all, delete-orphan"))
    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     nullable=True)
    user = relationship(User,
                        backref=backref("traffic_volumes",
                                        cascade="all, delete-orphan"),
                        uselist=False)
    packets = Column(Integer, CheckConstraint('amount >= 0'),
                     nullable=False)


class PmacctTable(ModelBase):
    __abstract__ = True
    packets = Column(BigInteger, nullable=False)
    bytes = Column(BigInteger, nullable=False)
    stamp_inserted = Column(DateTime(timezone=True), nullable=False)
    stamp_updated = Column(DateTime(timezone=True))


class PmacctTrafficEgress(PmacctTable):
    ip_src = Column(IPAddress, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('ip_src', 'stamp_inserted'),
    )


ddl.add_rule(
    PmacctTrafficEgress.__table__,
    Rule("pmacct_traffic_egress_insert", PmacctTrafficEgress.__table__, "INSERT",
         """
         INSERT INTO traffic_volume (type, ip_id, "timestamp", amount, packets, user_id)
         SELECT 'Egress',
             ip.id,
             new.stamp_inserted,
             new.bytes,
             new.packets,
             host.owner_id
            FROM ip
              JOIN interface ON ip.interface_id = interface.id
              JOIN host ON interface.host_id = host.id
         WHERE new.ip_src = ip.address
         """,
         do_instead=True)
)

# The rule demands that `traffic_volume` already has been added
PmacctTrafficEgress.__table__.add_is_dependent_on(TrafficVolume.__table__)


class PmacctTrafficIngress(PmacctTable):
    ip_dst = Column(IPAddress, nullable=False)
    __table_args__ = (
        PrimaryKeyConstraint('ip_dst', 'stamp_inserted'),
    )


ddl.add_rule(
    PmacctTrafficIngress.__table__,
    Rule("pmacct_traffic_ingress_insert", PmacctTrafficIngress.__table__, "INSERT",
         """
         INSERT INTO traffic_volume (type, ip_id, "timestamp", amount, packets, user_id)
         SELECT 'Ingress',
             ip.id,
             new.stamp_inserted,
             new.bytes,
             new.packets,
             host.owner_id
            FROM ip
              JOIN interface ON ip.interface_id = interface.id
              JOIN host ON interface.host_id = host.id
         WHERE new.ip_dst = ip.address
         """,
         do_instead=True)
)

# The rule demands that `traffic_volume` already has been added
PmacctTrafficIngress.__table__.add_is_dependent_on(TrafficVolume.__table__)


class TrafficCredit(TrafficEvent, IntegerIdModel):
    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     nullable=False)
    user = relationship(User,
                        backref=backref("traffic_credits",
                                        cascade="all, delete-orphan"),
                        uselist=False)

ddl.register()
