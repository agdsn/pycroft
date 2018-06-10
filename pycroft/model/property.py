# -*- coding: utf-8 -*-
# Copyright (c) 2018 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.property
~~~~~~~~~~~~~~~~~~~~~~

This module contains model descriptions concerning properties, groups, and memberships.

"""
from sqlalchemy import null, and_, or_, func, Column, Integer, String, union, literal
from sqlalchemy.orm import Query

from .base import ModelBase
from .ddl import View, DDLManager
from .functions import utcnow as utcnow_sql
from .user import User, Property, Membership, PropertyGroup

manager = DDLManager()

current_property = View(
    name='current_property',
    #metadata=ModelBase.metadata,
    query=union(
        Query([User.id.label('user_id'), Property.name.label('property_name'),
               literal(False).label('denied')])
        .select_from(Membership)
        .join(PropertyGroup)
        .join(User)
        .filter(and_(
            or_(Membership.begins_at == null(), Membership.begins_at <= utcnow_sql()),
            or_(Membership.ends_at == null(), utcnow_sql() <= Membership.ends_at),
        ))
        .join(Property)
        .group_by(User.id, Property.name)
        .having(func.every(Property.granted))
        .statement,

        Query([User.id.label('user_id'), Property.name.label('property_name'),
               literal(True).label('denied')])
        .select_from(Membership)
        .join(PropertyGroup)
        .join(User)
        .filter(and_(
            or_(Membership.begins_at == null(), Membership.begins_at <= utcnow_sql()),
            or_(Membership.ends_at == null(), utcnow_sql() <= Membership.ends_at),
        ))
        .join(Property)
        .group_by(User.id, Property.name)
        # granted by ≥1 membership, but also denied by ≥1 membership
        .having(and_(func.bool_or(Property.granted), ~func.every(Property.granted)))
        .statement,
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
