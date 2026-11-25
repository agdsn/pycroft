# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model
~~~~~~~~~~~~~~

This package contains basic stuff for db actions.

:copyright: (c) 2011 by AG DSN.
"""

import typing as t
from datetime import timezone, tzinfo

from sqlalchemy import create_engine as sqa_create_engine, Connection
from sqlalchemy.future import Engine

from . import _all
from . import base
from . import session


def create_engine(connection_string, **kwargs) -> Engine:
    kwargs.setdefault("connect_args", {}).update(
        options=r"-c TimeZone=UTC -c search_path=pycroft,\ public",
    )
    return sqa_create_engine(connection_string, isolation_level="SERIALIZABLE", **kwargs)


def create_db_model(bind: Connection) -> None:
    """Create all models in the database."""
    # skip objects marked with "is_view"
    tables = [
        table
        for table in base.ModelBase.metadata.tables.values()
        if not table.info.get("is_view", False)
    ]
    base.ModelBase.metadata.create_all(bind, tables=tables)


def drop_db_model(bind: Connection) -> None:
    """Drop all models from the database."""
    # skip objects marked with "is_view"
    tables = [
        table
        for table in base.ModelBase.metadata.tables.values()
        if not table.info.get("is_view", False)
    ]

    base.ModelBase.metadata.drop_all(bind, tables=tables)
