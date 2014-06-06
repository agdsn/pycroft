# -*- coding: utf-8 -*-
"""
    pycroft.model.base
    ~~~~~~~~~~~~~~

    This module contains base stuff for all models.

    :copyright: (c) 2011 by AG DSN.
"""
import re
from sqlalchemy import Column
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.types import Integer

_session = None


class _ModelMeta(DeclarativeMeta):
    """Metaclass for all mapped Database objects."""
    @property
    def q(cls):
        """This is a shortcut for easy querying of whole objects.

        With this metaclass shortcut you can query a Model with
        Model.q.filter(...) without using the verbose session stuff
        """
        global _session
        if _session is None or not _session.active:
            import pycroft.model.session
            _session = pycroft.model.session.session
        return _session.query(cls)


class _Base(object):
    """Baseclass for all database models."""
    id = Column(Integer, primary_key=True)

    @declared_attr
    def __tablename__(cls):
        """Autogenerate the tablename for the mapped objects."""
        return cls._to_snake_case(cls.__name__)

    @staticmethod
    def _to_snake_case(name):
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', name)
        name = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', name)
        return name.lower()

    def __repr__(self):
        return "{0}.{1}({2})".format(
            self.__module__,
            self.__class__.__name__,
            ", ".join(key + "=" + repr(getattr(self, key, "<unknown>"))
                      for key in self.__mapper__.columns.keys())
        )


ModelBase = declarative_base(cls=_Base, metaclass=_ModelMeta)
