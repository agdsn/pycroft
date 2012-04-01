# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.session
    ~~~~~~~~~~~~~~

    This module contains the session stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""

from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine


class SessionWrapper(object):
    def __init__(self, autocommit=False, autoflush=True):
        self._engine = create_engine("sqlite:///test_db.sqlite", echo=False)
        self._scoped_session = scoped_session(sessionmaker(bind=self._engine,
                                                           autocommit=autocommit,
                                                           autoflush=autoflush))

    def __getattr__(self, item):
        return getattr(self._scoped_session, item)

    def get_engine(self):
        return self._engine


session = SessionWrapper()
