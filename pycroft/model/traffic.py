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
from pycroft.model.host import IP, Host, Interface

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
    packets = Column(Integer, CheckConstraint('packets >= 0'),
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
         # We use an ugly-ass format string to have an additional
         # safety net when refactoring e.g. column names
         """
         INSERT INTO traffic_volume ({tv_type}, {tv_ip_id}, "{tv_timestamp}", {tv_amount}, {tv_packets}, {tv_user_id})
         SELECT 'Egress',
             {ip_id},
             new.{pm_stamp_inserted},
             new.{pm_bytes},
             new.{pm_packets},
             {host_owner_id}
            FROM ip
              JOIN {interface_tname} ON {ip_interface_id} = {interface_id}
              JOIN {host_tname} ON {interface_host_id} = {host_id}
         WHERE new.{pm_ip_src} = {ip_address}
         """.format(
             tv_type=TrafficVolume.type.key,
             tv_ip_id=TrafficVolume.ip_id.key,
             tv_timestamp=TrafficVolume.timestamp.key,
             tv_amount=TrafficVolume.amount.key,
             tv_packets=TrafficVolume.packets.key,
             tv_user_id=TrafficVolume.user_id.key,
             pm_stamp_inserted=PmacctTrafficEgress.stamp_inserted.key,
             pm_bytes=PmacctTrafficEgress.bytes.key,
             pm_packets=PmacctTrafficEgress.packets.key,
             pm_ip_src=PmacctTrafficEgress.ip_src.key,
             ip_tname=IP.__tablename__,
             ip_id=str(IP.id.expression),
             ip_interface_id=str(IP.interface_id.expression),
             ip_address=str(IP.address.expression),
             host_tname=Host.__tablename__,
             host_id=str(Host.id.expression),
             host_owner_id=str(Host.owner_id.expression),
             interface_tname=Interface.__tablename__,
             interface_id=str(Interface.id.expression),
             interface_host_id=str(Interface.host_id.expression),
         ),
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
         # concerning the format string, see above comment
         """
         INSERT INTO traffic_volume ({tv_type}, {tv_ip_id}, "{tv_timestamp}", {tv_amount}, {tv_packets}, {tv_user_id})
         SELECT 'Ingress',
             {ip_id},
             new.{pm_stamp_inserted},
             new.{pm_bytes},
             new.{pm_packets},
             {host_owner_id}
            FROM ip
              JOIN {interface_tname} ON {ip_interface_id} = {interface_id}
              JOIN {host_tname} ON {interface_host_id} = {host_id}
         WHERE new.{pm_ip_dst} = {ip_address}
         """.format(
             tv_type=TrafficVolume.type.key,
             tv_ip_id=TrafficVolume.ip_id.key,
             tv_timestamp=TrafficVolume.timestamp.key,
             tv_amount=TrafficVolume.amount.key,
             tv_packets=TrafficVolume.packets.key,
             tv_user_id=TrafficVolume.user_id.key,
             pm_stamp_inserted=PmacctTrafficIngress.stamp_inserted.key,
             pm_bytes=PmacctTrafficIngress.bytes.key,
             pm_packets=PmacctTrafficIngress.packets.key,
             pm_ip_dst=PmacctTrafficIngress.ip_dst.key,
             ip_tname=IP.__tablename__,
             ip_id=str(IP.id.expression),
             ip_interface_id=str(IP.interface_id.expression),
             ip_address=str(IP.address.expression),
             host_tname=Host.__tablename__,
             host_id=str(Host.id.expression),
             host_owner_id=str(Host.owner_id.expression),
             interface_tname=Interface.__tablename__,
             interface_id=str(Interface.id.expression),
             interface_host_id=str(Interface.host_id.expression),
         ),
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
