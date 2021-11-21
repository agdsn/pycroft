# Copyright (c) 2018 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.property
~~~~~~~~~~~~~~~~~~~~~~

This module contains model descriptions concerning properties, groups, and memberships.

"""
from datetime import datetime
from typing import Optional

from sqlalchemy.sql.selectable import TableValuedAlias

from pycroft.model import ddl
from sqlalchemy import null, and_, or_, func, Column, Integer, String, union, \
    literal, literal_column, select
from sqlalchemy.orm import Query

from .base import ModelBase
from .ddl import View, DDLManager
from .user import User, Property, Membership, PropertyGroup

manager = DDLManager()

property_query_stmt = union(
    Query([User.id.label('user_id'), Property.name.label('property_name'),
           literal(False).label('denied')])
    .select_from(Membership)
    .join(PropertyGroup)
    .join(User)
    .filter(Membership.active_during.contains(literal_column('evaluation_time')))
    .join(Property)
    .group_by(User.id, Property.name)
    .having(func.every(Property.granted))
    .statement,

    Query([User.id.label('user_id'), Property.name.label('property_name'),
           literal(True).label('denied')])
    .select_from(Membership)
    .join(PropertyGroup)
    .join(User)
    .filter(Membership.active_during.contains(literal_column('evaluation_time')))
    .join(Property)
    .group_by(User.id, Property.name)
    # granted by ≥1 membership, but also denied by ≥1 membership
    # NB: this does NOT include properties in the list that were ONLY denied, but never granted!
    .having(and_(func.bool_or(Property.granted), ~func.every(Property.granted)))
    .statement,
)

evaluate_properties_function = ddl.Function(
    'evaluate_properties', ['evaluation_time timestamp with time zone'],
    'TABLE (user_id INT, property_name VARCHAR(255), denied BOOLEAN)',
    definition=property_query_stmt,
    volatility='stable',
)

manager.add_function(
    Membership.__table__,
    evaluate_properties_function
)


def evaluate_properties(when: datetime | None = None, name='properties') -> TableValuedAlias:
    """A sqlalchemy `func` wrapper for the `evaluate_properties` PSQL function.

    See `sqlalchemy.sql.selectable.FromClause.table_valued`.
    """
    return func.evaluate_properties(when)\
        .table_valued('user_id', 'property_name', 'denied', name=name)


_current_props = evaluate_properties(func.current_timestamp())
current_property = View(
    name='current_property',
    #metadata=ModelBase.metadata,
    query=(
        select(_current_props.c.user_id,
               _current_props.c.property_name,
               _current_props.c.denied)
        .select_from(_current_props)
    ),
)
manager.add_view(Membership.__table__, current_property)


class CurrentProperty(ModelBase):
    __table__ = current_property.table
    __mapper_args__ = {
        'primary_key': (current_property.table.c.user_id,
                        current_property.table.c.property_name),
    }


manager.register()
