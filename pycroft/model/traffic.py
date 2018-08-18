# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, ForeignKey, CheckConstraint, \
    PrimaryKeyConstraint, func, or_, and_, true, literal, literal_column, \
    union_all, select, cast, TIMESTAMP, TEXT
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql.expression import case
from sqlalchemy.orm import relationship, backref, Query
from sqlalchemy.types import BigInteger, Enum, Integer

from pycroft.model.base import ModelBase, IntegerIdModel
from pycroft.model.ddl import DDLManager, Function, Trigger, View
from pycroft.model.types import IPAddress, DateTimeTz
from pycroft.model.user import User
from pycroft.model.host import IP, Host, Interface

ddl = DDLManager()


class TrafficBalance(ModelBase):
    user_id = Column(Integer, ForeignKey(User.id, ondelete="CASCADE"),
                     primary_key=True)
    user = relationship(User,
                        backref=backref("_traffic_balance", uselist=False))
    amount = Column(BigInteger, nullable=False)
    timestamp = Column(DateTimeTz, server_default=func.current_timestamp(), nullable=False)


class TrafficEvent(object):
    timestamp = Column(DateTimeTz, server_default=func.current_timestamp(), nullable=False)
    amount = Column(BigInteger, CheckConstraint('amount >= 0'),
                    nullable=False)


class TrafficVolume(TrafficEvent, ModelBase):
    __table_args__ = (
        PrimaryKeyConstraint('ip_id', 'type', 'timestamp'),
    )
    type = Column(Enum("Ingress", "Egress", name="traffic_direction"),
                  nullable=False)
    ip_id = Column(Integer, ForeignKey(IP.id, ondelete="CASCADE"),
                   nullable=False, index=True)
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

def traffic_history_query():
    timestamptz = TIMESTAMP(timezone=True)

    events = union_all(
        select([TrafficCredit.amount,
                TrafficCredit.timestamp,
                literal("Credit").label('type')]
               ).where(TrafficCredit.user_id == literal_column('arg_user_id')),

        select([(-TrafficVolume.amount).label('amount'),
                TrafficVolume.timestamp,
                cast(TrafficVolume.type, TEXT).label('type')]
               ).where(TrafficVolume.user_id == literal_column('arg_user_id'))
    ).cte('traffic_events')

    def round_time(time_expr, ceil=False):
        round_func = func.ceil if ceil else func.trunc
        step_epoch = func.extract('epoch', literal_column('arg_step'))
        return cast(func.to_timestamp(round_func(func.extract('epoch', time_expr) / step_epoch) * step_epoch), timestamptz)

    balance = select([TrafficBalance.amount, TrafficBalance.timestamp])\
        .select_from(User.__table__.outerjoin(TrafficBalance))\
        .where(User.id == literal_column('arg_user_id'))\
        .cte('balance')

    balance_amount = select([balance.c.amount]).as_scalar()
    balance_timestamp = select([balance.c.timestamp]).as_scalar()

    # Bucket layout
    # n = interval / step
    # 0: Aggregates all prior traffic_events so that the balance value can be calculated
    # 1 - n: Traffic history entry
    # n+1: Aggregates all data after the last point in time, will be discarded
    buckets = select([literal_column('bucket'),
            (func.row_number().over(order_by=literal_column('bucket')) - 1).label('index')]
    ).select_from(
        func.generate_series(
            round_time(cast(literal_column('arg_start'), timestamptz)) - literal_column('arg_step'),
            round_time(cast(literal_column('arg_start'), timestamptz) + literal_column('arg_interval')),
            literal_column('arg_step')
        ).alias('bucket')
    ).order_by(
        literal_column('bucket')
    ).cte('buckets')

    def cond_sum(condition, label, invert=False):
        return func.sum(case(
            [(condition, events.c.amount if not invert else -events.c.amount)],
            else_=None)).label(label)


    hist = select([buckets.c.bucket,
                   cond_sum(events.c.type == 'Credit', 'credit'),
                   cond_sum(events.c.type == 'Ingress', 'ingress', invert=True),
                   cond_sum(events.c.type == 'Egress', 'egress', invert=True),
                   func.sum(events.c.amount).label('amount'),
                   cond_sum(and_(balance_timestamp != None, events.c.timestamp < balance_timestamp), 'before_balance'),
                   cond_sum(or_(balance_timestamp == None, events.c.timestamp >= balance_timestamp), 'after_balance')]
    ).select_from(buckets.outerjoin(
        events, func.width_bucket(
            events.c.timestamp, select([func.array(select([buckets.c.bucket]).select_from(buckets).where(buckets.c.index != 0).label('dummy'))])
        ) == buckets.c.index
    )).where(
        # Discard bucket n+1
        buckets.c.index < select([func.max(buckets.c.index)])
    ).group_by(
        buckets.c.bucket
    ).order_by(
        buckets.c.bucket
    ).cte('traffic_hist')


    # Bucket is located before the balance and no traffic_events exist before it
    first_event_timestamp = select([func.min(events.c.timestamp)]).as_scalar()
    case_before_balance_no_data = (
        and_(balance_timestamp != None, hist.c.bucket < balance_timestamp,
        or_(first_event_timestamp == None,
            hist.c.bucket < first_event_timestamp
            )),
        None
    )

    # Bucket is located after the balance
    case_after_balance = (
        or_(balance_timestamp == None, hist.c.bucket >= balance_timestamp),
        func.coalesce(balance_amount, 0) + func.coalesce(
            func.sum(hist.c.after_balance).over(
                order_by=hist.c.bucket.asc(), rows=(None, 0)),
            0)
    )

    # Bucket is located before the balance, but there still exist traffic_events before it
    else_before_balance = (
            func.coalesce(balance_amount, 0) +
            func.coalesce(hist.c.after_balance, 0) -
            func.coalesce(
                func.sum(hist.c.before_balance).over(
                    order_by=hist.c.bucket.desc(), rows=(None, -1)
                ), 0)
    )

    agg_hist = select(
            [hist.c.bucket, hist.c.credit, hist.c.ingress, hist.c.egress, case(
            [case_before_balance_no_data, case_after_balance],
            else_=else_before_balance
        ).label('balance')]).alias('agg_hist')

    # Remove bucket 0
    result = select([agg_hist]).order_by(agg_hist.c.bucket).offset(1)

    return result


traffic_history_function = Function(
    'traffic_history', ['arg_user_id int', 'arg_start timestamptz', 'arg_interval interval', 'arg_step interval'],
    'TABLE ("timestamp" timestamptz, credit numeric, ingress numeric, egress numeric, balance numeric)',
    str(
        traffic_history_query().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={'literal_binds': True}
        )
    ),
    volatility='stable',
)

ddl.add_function(
    TrafficBalance.__table__,
    traffic_history_function
)


class TrafficHistoryEntry:
    def __init__(self, timestamp, credit, ingress, egress, balance):
        self.timestamp = timestamp
        self.credit = credit
        self.ingress = ingress
        self.egress = egress
        self.balance = balance

    def __repr__(self):
        return str(self.__dict__)

ddl.register()
