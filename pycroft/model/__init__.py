# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model
    ~~~~~~~~~~~~~~

    This module contains basic stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""

from pycroft.model import base, session
# this imports are needed!!!
from pycroft.model import accounting
from pycroft.model import dormitory
from pycroft.model import finance
from pycroft.model import hosts
from pycroft.model import logging
from pycroft.model import ports
from pycroft.model import rights
from pycroft.model import user


def create_db_model():
    """Create all models in the database.
    """
    base.ModelBase.metadata.create_all(session.session.get_engine())


def drop_db_model():
    """Drop all models from the database.
    """
    base.ModelBase.metadata.drop_all(session.session.get_engine())
