# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, CheckConstraint, \
    PrimaryKeyConstraint, Index, DDL
from sqlalchemy.orm import relationship, backref, Query
from sqlalchemy.types import BigInteger, Enum, Integer, DateTime

from pycroft.model.base import ModelBase, IntegerIdModel
from pycroft.model.ddl import DDLManager, Function, Trigger, View
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


class TrafficVolume(TrafficEvent, ModelBase):
    __table_args__ = (
        PrimaryKeyConstraint('ip_id', 'type', 'timestamp'),
        Index('user_id', 'timestamp'),
    )
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
TrafficVolume.__table__.add_is_dependent_on(IP.__table__)

class PmacctTable(ModelBase):
    __abstract__ = True
    packets = Column(BigInteger, nullable=False)
    bytes = Column(BigInteger, nullable=False)
    stamp_inserted = Column(DateTime(timezone=True), nullable=False)
    stamp_updated = Column(DateTime(timezone=True))


pmacct_traffic_egress = View(
    name='pmacct_traffic_egress',
    metadata=ModelBase.metadata,
    query=(
        Query([])
            .add_columns(TrafficVolume.packets.label('packets'),
                         TrafficVolume.amount.label('bytes'),
                         TrafficVolume.timestamp.label('stamp_inserted'),
                         TrafficVolume.timestamp.label('stamp_updated'),
                         IP.address.label('ip_src'))
            .select_from(TrafficVolume)
            .filter_by(type='Egress')
            .join(IP)
            .statement  # turns our `Selectable` into something compilable
    ),
)
ddl.add_view(TrafficVolume.__table__, pmacct_traffic_egress)

pmacct_egress_upsert = Function(
    name="pmacct_traffic_egress_insert", arguments=[], language="plpgsql", rtype="trigger",
    definition="""BEGIN
        INSERT INTO traffic_volume (type, ip_id, "timestamp", amount, packets, user_id)
        SELECT
            'Egress',
            ip.id,
            date_trunc('day', NEW.stamp_inserted),
            NEW.bytes,
            NEW.packets,
            host.owner_id
        FROM ip
        JOIN interface ON ip.interface_id = interface.id
        JOIN host ON interface.host_id = host.id
        WHERE NEW.ip_src = ip.address
        ON CONFLICT (ip_id, type, "timestamp")
        DO UPDATE SET (amount, packets) = (traffic_volume.amount + NEW.bytes,
                                           traffic_volume.packets + NEW.packets);
    RETURN NULL;
    END;"""
)
pmacct_egress_upsert_trigger = Trigger(
    name='pmacct_traffic_egress_insert_trigger', table=pmacct_traffic_egress.table,
    events=["INSERT"], function_call="pmacct_traffic_egress_insert()", when="INSTEAD OF"
)

ddl.add_function(TrafficVolume.__table__, pmacct_egress_upsert)
ddl.add_trigger(TrafficVolume.__table__, pmacct_egress_upsert_trigger)


pmacct_traffic_ingress = View(
    name='pmacct_traffic_ingress',
    metadata=ModelBase.metadata,
    query=(
        Query([])
            .add_columns(TrafficVolume.packets.label('packets'),
                         TrafficVolume.amount.label('bytes'),
                         TrafficVolume.timestamp.label('stamp_inserted'),
                         TrafficVolume.timestamp.label('stamp_updated'),
                         IP.address.label('ip_dst'))
            .select_from(TrafficVolume)
            .filter_by(type='Ingress')
            .join(IP)
            .statement  # turns our `Selectable` into something compilable
    ),
)
ddl.add_view(TrafficVolume.__table__, pmacct_traffic_ingress)


pmacct_ingress_upsert = Function(
    name="pmacct_traffic_ingress_insert", arguments=[], language="plpgsql", rtype="trigger",
    definition="""BEGIN
        INSERT INTO traffic_volume (type, ip_id, "timestamp", amount, packets, user_id)
        SELECT
            'Ingress',
            ip.id,
            date_trunc('day', NEW.stamp_inserted),
            NEW.bytes,
            NEW.packets,
            host.owner_id
        FROM ip
        JOIN interface ON ip.interface_id = interface.id
        JOIN host ON interface.host_id = host.id
        WHERE NEW.ip_dst = ip.address
        ON CONFLICT (ip_id, type, "timestamp")
        DO UPDATE SET (amount, packets) = (traffic_volume.amount + NEW.bytes,
                                           traffic_volume.packets + NEW.packets);
    RETURN NULL;
    END;"""
)
pmacct_ingress_upsert_trigger = Trigger(
    name='pmacct_traffic_ingress_insert_trigger', table=pmacct_traffic_ingress.table,
    events=["INSERT"], function_call="pmacct_traffic_ingress_insert()", when="INSTEAD OF"
)

ddl.add_function(TrafficVolume.__table__, pmacct_ingress_upsert)
ddl.add_trigger(TrafficVolume.__table__, pmacct_ingress_upsert_trigger)


class TrafficCredit(TrafficEvent, IntegerIdModel):
    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     nullable=False)
    user = relationship(User,
                        backref=backref("traffic_credits",
                                        cascade="all, delete-orphan"),
                        uselist=False)

ddl.register()
