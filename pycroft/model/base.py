# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.base
    ~~~~~~~~~~~~~~~~~~

    This module contains base stuff for all models.

    :copyright: (c) 2011 by AG DSN.
"""
import re

from sqlalchemy import String
from sqlalchemy.orm import declared_attr, Query, DeclarativeBase, Mapped, mapped_column

from pycroft.model.session import session
from pycroft.model.type_aliases import str50, str255, str40


class _ModelMeta(type(DeclarativeBase)):
    """Metaclass for all mapped Database objects."""
    @property
    def q(cls):
        """This is a shortcut for easy querying of whole objects.

        With this metaclass shortcut you can query a Model with
        Model.q.filter(...) without using the verbose session stuff
        """
        return session.query(cls)


class ModelBase(DeclarativeBase, metaclass=_ModelMeta):
    """Base class for all database models."""

    type_annotation_map = {
        str40: String(40),
        str50: String(50),
        str255: String(255),
        # does not work yet: see https://github.com/sqlalchemy/sqlalchemy/issues/9175
        # utc.DateTimeTz: pycroft_sqla_types.DateTimeTz,
    }

    @classmethod
    def get(cls, *a, **kw):
        """This is a shortcut for `session.get(cls, –)`"""
        return session.get(cls, *a, **kw)

    def __init__(self, **kwargs):
        # workaround, see https://github.com/sqlalchemy/sqlalchemy/issues/9171
        self.registry.constructor(self, **kwargs)

    @declared_attr
    def __tablename__(cls) -> str:
        """Autogenerate the tablename for the mapped objects."""
        return cls._to_snake_case(cls.__name__)

    @staticmethod
    def _to_snake_case(name):
        name = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', name)
        name = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', name)
        return name.lower()

    def __repr__(self):
        return "{}.{}({})".format(
            self.__module__, self.__class__.__name__,
            ", ".join("{}={!r}".format(key, getattr(self, key, "<unknown>"))
                      for key in self.__mapper__.columns.keys()
                      if 'passwd' not in key and 'password' not in key)
        )

    def __str__(self):
        return "{}({})".format(
            self.__class__.__name__,
            ", ".join("{}={}".format(key, getattr(self, key, "<unknown>"))
                      for key in self.__mapper__.columns.keys()
                      if 'passwd' not in key and 'password' not in key)
        )

    # __table__: Table

    import typing
    if typing.TYPE_CHECKING:
        # uncomment that to get the deprecation warnings.
        # unfortunately, this breaks mypy linting because we can't
        # reinterpret a `Callable` as something else, say using a cast.
        # @classmethod
        # def q(cls):
        #     import warnings
        #     warnings.warn("Deprecated: Use `session.execute()` and `select()` instead",
        #                   DeprecationWarning)
        q: Query

        T = typing.TypeVar('T', bound='ModelBase')

        @classmethod
        def get(cls: type[T], *a, **kw) -> T:
            pass

class IntegerIdModel(ModelBase):
    """
    Abstract base class for database models with an Integer primary column,
    named ``id``.
    """

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
