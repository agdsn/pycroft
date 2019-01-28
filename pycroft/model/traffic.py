# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from sqlalchemy import Column, ForeignKey, CheckConstraint, \
    PrimaryKeyConstraint, func, or_, and_, true, literal_column, \
    select, cast, TEXT
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, backref, Query
from sqlalchemy.types import BigInteger, Enum, Integer

from pycroft.model.base import ModelBase
from pycroft.model.ddl import DDLManager, Function, Trigger, View
from pycroft.model.types import DateTimeTz
from pycroft.model.user import User
from pycroft.model.host import IP, Host, Interface

ddl = DDLManager()


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


def traffic_history_query():
    events = (select([func.sum(TrafficVolume.amount).label('amount'),
                      literal_column('day'),
                      cast(TrafficVolume.type, TEXT).label('type')]
                     )
              .select_from(
                    func.generate_series(
                        func.date_trunc('day', literal_column('arg_start')),
                        func.date_trunc('day', literal_column('arg_end')),
                        '1 day'
                    ).alias('day')
                    .outerjoin(TrafficVolume.__table__, and_(
                        func.date_trunc('day', TrafficVolume.timestamp) == literal_column('day'),
                        TrafficVolume.user_id == literal_column('arg_user_id'))
                    )
              )
              .group_by(literal_column('day'), literal_column('type'))
              ).cte()

    events_ingress = select([events]).where(or_(events.c.type == 'Ingress', events.c.type == None)).cte()
    events_egress = select([events]).where(or_(events.c.type == 'Egress', events.c.type == None)).cte()

    hist = (select([func.coalesce(events_ingress.c.day, events_egress.c.day).label('timestamp'),
                    events_ingress.c.amount.label('ingress'),
                    events_egress.c.amount.label('egress')])
            .select_from(events_ingress.join(events_egress,
                                             events_ingress.c.day == events_egress.c.day,
                                             full=true))
            .order_by(literal_column('timestamp'))
            )

    return hist


traffic_history_function = Function(
    'traffic_history', ['arg_user_id int', 'arg_start timestamptz', 'arg_end timestamptz'],
    'TABLE ("timestamp" timestamptz, ingress numeric, egress numeric)',
    str(
        traffic_history_query().compile(
            dialect=postgresql.dialect(),
            compile_kwargs={'literal_binds': True}
        )
    ),
    volatility='stable',
)

ddl.add_function(
    TrafficVolume.__table__,
    traffic_history_function
)


class TrafficHistoryEntry:
    def __init__(self, timestamp, ingress, egress):
        self.timestamp = timestamp
        self.ingress = ingress
        self.egress = egress

    def __repr__(self):
        return str(self.__dict__)


ddl.register()
