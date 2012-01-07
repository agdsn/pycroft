# -*- coding: utf-8 -*-
"""
    pycroft.model
    ~~~~~~~~~~~~~~

    This package contains basic stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""

import base
import session


def create_db_model():
    """Create all models in the database.
    """
    base.ModelBase.metadata.create_all(session.session.get_engine())


def drop_db_model():
    """Drop all models from the database.
    """
    base.ModelBase.metadata.drop_all(session.session.get_engine())
