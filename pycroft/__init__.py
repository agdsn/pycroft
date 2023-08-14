# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""

:copyright: (c) 2011 by AG DSN.

What belongs in this package
----------------------------
This is the “backend” package, and as such mainly contains

* things related to the ``pycroft`` business logic (i.e., :mod:`pycroft.lib`)
* a definition of the database model (i.e., :mod:`pycroft.model`).

In particular, this means that *at no point* should there be any dependencies to ``flask`` or
other frontend-specific libraries.
"""
import typing

from sqlalchemy.orm.exc import NoResultFound
from werkzeug.local import LocalProxy
from pycroft.model.config import Config


def _get_config():
    config = Config.get(1)
    if config is None:
        raise NoResultFound
    return config


config: Config = typing.cast(Config, LocalProxy(_get_config))
