# -*- coding: utf-8 -*-
"""
    pycroft.model
    ~~~~~~~~~~~~~~

    This module contains basic stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""

def create_db_model():
    """Create all models in the database.

    """
    from pycroft.model import base, session
    base.ModelBase.metadata.create_all(session.session.get_engine())


def drop_db_model():
    """Drop all models from the database.

    """
    from pycroft.model import base, session
    base.ModelBase.metadata.drop_all(session.session.get_engine())