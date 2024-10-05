# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.session
    ~~~~~~~~~~~~~~~~~~~~~

    This module contains the session stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""
import typing as t
from typing import overload, Any, TYPE_CHECKING
from collections.abc import Callable

from sqlalchemy.orm import scoped_session
from sqlalchemy.sql.functions import AnsiFunction
from werkzeug.local import LocalProxy
import wrapt

from sqlalchemy import func, orm

from pycroft.helpers.utc import DateTimeTz


class NullScopedSession:
    def __getattr__(self, item):
        raise AttributeError("Session has not been initialized.")

    def __call__(self, *args, **kwargs):
        raise AttributeError("Session has not been initialized.")

    def remove(self):
        pass


Session: scoped_session[orm.Session] = t.cast(
    scoped_session[orm.Session], LocalProxy(lambda: NullScopedSession())
)
session: orm.Session = t.cast(orm.Session, LocalProxy(lambda: Session()))

if TYPE_CHECKING:
    def session():
        import warnings

        warnings.warn(
            "Deprecated: Use dependency injection instead"
            " (i.e. pass the session explicitly via a parameter)",
            DeprecationWarning,
            stacklevel=1,
        )


def set_scoped_session(scoped_session: scoped_session[orm.Session]) -> None:
    Session.remove()
    object.__setattr__(Session, "_LocalProxy__wrapped", lambda: scoped_session)
    object.__setattr__(Session, "_get_current_object", lambda: scoped_session)


# noinspection PyOverloads
@overload
def with_transaction[F: Callable[..., Any]](wrapped: F) -> F: ...


@wrapt.decorator
def with_transaction(wrapped, instance, args, kwargs):
    transaction = session.begin_nested()
    try:
        rv = wrapped(*args, **kwargs)
        transaction.commit()
        return rv
    except:
        transaction.rollback()
        raise


def utcnow() -> DateTimeTz:
    return session.query(func.current_timestamp()).scalar()


def current_timestamp() -> AnsiFunction[DateTimeTz]:
    return t.cast(AnsiFunction[DateTimeTz], func.current_timestamp())
