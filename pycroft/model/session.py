# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.session
    ~~~~~~~~~~~~~~

    This module contains the session stuff for db actions.

    :copyright: (c) 2011 by AG DSN.
"""

from werkzeug.local import LocalProxy
import wrapt

from sqlalchemy import func


class NullScopedSession(object):
    def __getattr__(self, item):
        raise AttributeError("Session has not been initialized.")

    def __call__(self, *args, **kwargs):
        raise AttributeError("Session has not been initialized.")

    def remove(self):
        pass


Session = LocalProxy(lambda: NullScopedSession())
session = LocalProxy(lambda: Session())


def set_scoped_session(scoped_session):
    Session.remove()
    # noinspection PyCallByClass
    object.__setattr__(Session, '_LocalProxy__local', lambda: scoped_session)


@wrapt.decorator
def with_transaction(wrapped, instance, args, kwargs):
    transaction = session.begin(subtransactions=True)
    try:
        rv = wrapped(*args, **kwargs)
        transaction.commit()
        return rv
    except:
        transaction.rollback()
        raise


def utcnow():
    return session.query(func.current_timestamp()).scalar()
