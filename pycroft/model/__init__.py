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

import os
from sqlalchemy import create_engine as sqa_create_engine


def create_engine(connection_string, **kwargs):
    kwargs.setdefault('connect_args', {}).update(
        options="-c TimeZone=UTC"
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
