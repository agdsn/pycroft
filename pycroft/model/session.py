# -*- coding: utf-8 -*-
"""
    pycroft.model.session
    ~~~~~~~~~~~~~~

    This module contains the session stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine


class SessionWrapper(object):
    def __init__(self):
        self._engine = create_engine("sqlite:///test_db.sqlite", echo=False)
        self._scoped_session = scoped_session(sessionmaker(bind=self._engine))

    def __getattr__(self, item):
        return getattr(self._scoped_session(), item)

    def get_engine(self):
        return self._engine


session = SessionWrapper()
