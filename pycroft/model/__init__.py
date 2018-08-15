# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model
    ~~~~~~~~~~~~~~

    This package contains basic stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""
from . import _all
from . import base
from . import session

from datetime import timezone, tzinfo

import os
import psycopg2.extensions
from sqlalchemy import create_engine as sqa_create_engine


class UTCTZInfoFactory(tzinfo):
    """
    A tzinfo factory compatible with :class:`psycopg2.tz.FixedOffsetTimezone`,
    that checks if the provided UTC offset is zero and returns
    :attr:`datetime.timezone.utc`. If the offset is not zero an
    :exc:`psycopg2.DataError` is raised.

    This class is implemented as a singleton that always returns the same
    instance.
    """

    def __new__(cls, offset):
        if offset != 0:
            raise psycopg2.DataError("UTC Offset is not zero: " + offset)
        return timezone.utc


class UTCTZInfoCursorFactory(psycopg2.extensions.cursor):
    """
    A Cursor factory that sets the
    :attr:`psycopg2.extensions.cursor.tzinfo_factory` to
    :class:`UTCTZInfoFactory`.

    The C implementation of the cursor class does not use the proper Python
    attribute lookup, therefore we have to set the instance variable rather
    than use a class attribute.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tzinfo_factory = UTCTZInfoFactory


def create_engine(connection_string, **kwargs):
    kwargs.setdefault('connect_args', {}).update(
        options="-c TimeZone=UTC", cursor_factory=UTCTZInfoCursorFactory
    )
    return sqa_create_engine(connection_string, **kwargs)


def create_db_model(bind):
    """Create all models in the database.
    """
    base.ModelBase.metadata.create_all(bind)


def drop_db_model(bind):
    """Drop all models from the database.
    """
    base.ModelBase.metadata.drop_all(bind)
