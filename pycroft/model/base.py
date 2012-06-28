# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.base
    ~~~~~~~~~~~~~~

    This module contains base stuff for all models.

    :copyright: (c) 2011 by AG DSN.
"""
from sqlalchemy import Column
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.types import Integer

_session = None


class _ModelMeta(DeclarativeMeta):
    """Metaclass for all mapped Database objects.
    """
    @property
    def q(cls):
        """This is a shortcut for easy querying of whole objects.

        With this metaclass shortcut you can query a Model with
        Model.q.filter(...) without using the verbose session stuff
        """
        global _session
        if _session is None:
            import pycroft.model.session
            _session = pycroft.model.session.session
        return _session.query(cls)


class _Base(object):
    """Baseclass for all database models.
    """
    id = Column(Integer, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        """Autogenerate the tablename for the mapped objects.
        """
        return cls.__name__.lower()


ModelBase = declarative_base(cls=_Base, metaclass=_ModelMeta)
