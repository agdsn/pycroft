# -*- coding: utf-8 -*-
# Copyright (c) 2011 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.base
    ~~~~~~~~~~~~~~

    This module contains base stuff for all models.

    :copyright: (c) 2011 by AG DSN.
"""

from sqlalchemy.ext.declarative import DeclarativeMeta, declarative_base, declared_attr

_session = None

class _ModelMeta(DeclarativeMeta):
    """Metaclass for all mapped Database objects.
    """
    
    @property
    def q(cls):
        """This is a shortcut for easy querying of qhole objects.

        With this metaclass shortcut you can query a Model with
        Model.q.filter(...) without using the verbose session stuff
        """
        if _session is None:
            global _session
            import pycroft.model.session
            _session = pycroft.model.session.session
        return _session.query(cls)



class _Base(object):
    """Baseclass sor all database models.
    
    """

    @declared_attr
    def __tablename__(cls):
        """Autogenerate the tablename for the mapped objects.

        """
        return cls.__name__.lower()



ModelBase = declarative_base(cls=_Base, metaclass=_ModelMeta)


from sqlalchemy import Integer, String, MetaData, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relation, backref
from sqlalchemy import Table, Column


class User(ModelBase):
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    login = Column(String(40))
    registration_date = Column(DateTime)
