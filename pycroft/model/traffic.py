# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, CheckConstraint, \
    PrimaryKeyConstraint, func, or_, and_, true
from sqlalchemy.orm import relationship, backref, Query
from sqlalchemy.types import BigInteger, Enum, Integer, DateTime

from pycroft.model.base import ModelBase, IntegerIdModel
from pycroft.model.ddl import DDLManager, Function, Trigger, View
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


class TrafficVolume(TrafficEvent, ModelBase):
    __table_args__ = (
        PrimaryKeyConstraint('ip_id', 'type', 'timestamp'),
    )
    type = Column(Enum("Ingress", "Egress", name="traffic_direction"),
                  nullable=False)
    ip_id = Column(Integer, ForeignKey(IP.id, ondelete="CASCADE"),
                   nullable=False)
    ip = relationship(IP, backref=backref("traffic_volumes",
                                          cascade="all, delete-orphan"))
    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     nullable=True, index=True)
    user = relationship(User,
                        backref=backref("traffic_volumes",
                                        cascade="all, delete-orphan"),
                        uselist=False)
    packets = Column(Integer, CheckConstraint('packets >= 0'),
                     nullable=False)
TrafficVolume.__table__.add_is_dependent_on(IP.__table__)
TrafficBalance.__table__.add_is_dependent_on(TrafficVolume.__table__)


pmacct_traffic_egress = View(
    name='pmacct_traffic_egress',
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

pmacct_expression_replacements = dict(
    tv_tname=TrafficVolume.__tablename__,
    tv_type=TrafficVolume.type.key,
    tv_ip_id=TrafficVolume.ip_id.key,
    tv_timestamp=TrafficVolume.timestamp.key,
    tv_amount=TrafficVolume.amount.key,
    tv_packets=TrafficVolume.packets.key,
    tv_user_id=TrafficVolume.user_id.key,
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
)
pmacct_egress_upsert = Function(
    name="pmacct_traffic_egress_insert", arguments=[], language="plpgsql", rtype="trigger",
    definition="""BEGIN
        INSERT INTO traffic_volume ({tv_type}, {tv_ip_id}, "{tv_timestamp}", {tv_amount}, {tv_packets}, {tv_user_id})
        SELECT
            'Egress',
            {ip_id},
            date_trunc('day', NEW.stamp_inserted),
            NEW.bytes,
            NEW.packets,
            {host_owner_id}
        FROM {ip_tname}
        JOIN {interface_tname} ON {ip_interface_id} = {interface_id}
        JOIN {host_tname} ON {interface_host_id} = {host_id}
        WHERE NEW.ip_src = {ip_address}
        ON CONFLICT ({tv_ip_id}, {tv_type}, "{tv_timestamp}")
        DO UPDATE SET ({tv_amount}, {tv_packets}) = ({tv_tname}.{tv_amount} + NEW.bytes,
                                                     {tv_tname}.{tv_packets} + NEW.packets);
    RETURN NULL;
    END;""".format(**pmacct_expression_replacements),
)
pmacct_egress_upsert_trigger = Trigger(
    name='pmacct_traffic_egress_insert_trigger', table=pmacct_traffic_egress.table,
    events=["INSERT"], function_call="pmacct_traffic_egress_insert()", when="INSTEAD OF"
)

ddl.add_function(TrafficVolume.__table__, pmacct_egress_upsert)
ddl.add_trigger(TrafficVolume.__table__, pmacct_egress_upsert_trigger)


pmacct_traffic_ingress = View(
    name='pmacct_traffic_ingress',
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
        INSERT INTO traffic_volume ({tv_type}, {tv_ip_id}, "{tv_timestamp}", {tv_amount}, {tv_packets}, {tv_user_id})
        SELECT
            'Ingress',
            {ip_id},
            date_trunc('day', NEW.stamp_inserted),
            NEW.bytes,
            NEW.packets,
            {host_owner_id}
        FROM {ip_tname}
        JOIN {interface_tname} ON {ip_interface_id} = {interface_id}
        JOIN {host_tname} ON {interface_host_id} = {host_id}
        WHERE NEW.ip_dst = {ip_address}
        ON CONFLICT ({tv_ip_id}, {tv_type}, "{tv_timestamp}")
        DO UPDATE SET ({tv_amount}, {tv_packets}) = ({tv_tname}.{tv_amount} + NEW.bytes,
                                                     {tv_tname}.{tv_packets} + NEW.packets);
    RETURN NULL;
    END;""".format(**pmacct_expression_replacements),
)
pmacct_ingress_upsert_trigger = Trigger(
    name='pmacct_traffic_ingress_insert_trigger', table=pmacct_traffic_ingress.table,
    events=["INSERT"], function_call="pmacct_traffic_ingress_insert()", when="INSTEAD OF"
)

ddl.add_function(TrafficVolume.__table__, pmacct_ingress_upsert)
ddl.add_trigger(TrafficVolume.__table__, pmacct_ingress_upsert_trigger)


class TrafficCredit(TrafficEvent, IntegerIdModel):
    user_id = Column(Integer, ForeignKey(User.id, ondelete='CASCADE'),
                     nullable=False, index=True)
    user = relationship(User,
                        backref=backref("traffic_credits",
                                        cascade="all, delete-orphan"),
                        uselist=False)
TrafficBalance.__table__.add_is_dependent_on(TrafficCredit.__table__)


recent_volume_q = (
    Query([func.sum(TrafficVolume.amount).label('amount')])
    .select_from(TrafficVolume)
    .filter(and_(User.id==TrafficVolume.user_id,
                 or_(TrafficBalance.user_id.is_(None),
                     TrafficBalance.timestamp <= TrafficVolume.timestamp)))
    .subquery()
    .lateral('recent_volume')
)

recent_credit_q = (
    Query([func.sum(TrafficCredit.amount).label('amount')])
    .select_from(TrafficCredit)
    .filter(and_(User.id==TrafficCredit.user_id,
                 or_(TrafficBalance.user_id.is_(None),
                     TrafficBalance.timestamp <= TrafficCredit.timestamp)))
    .subquery()
    .lateral('recent_credit')
)

current_traffic_balance_view = View(
    name='current_traffic_balance',
    query=(
        Query([
            User.id.label('user_id'),
            (func.coalesce(TrafficBalance.amount, 0) +
             func.coalesce(recent_credit_q.c.amount, 0) -
             func.coalesce(recent_volume_q.c.amount, 0)).label('amount'),
        ])
        .select_from(User)
        .outerjoin(TrafficBalance)
        .outerjoin(recent_credit_q, true())
        .outerjoin(recent_volume_q, true())
        .statement
    )
)
ddl.add_view(TrafficBalance.__table__, current_traffic_balance_view)


class CurrentTrafficBalance(ModelBase):
    __table__ = current_traffic_balance_view.table
    __mapper_args__ = {
        'primary_key': current_traffic_balance_view.table.c.user_id,
    }


ddl.register()
