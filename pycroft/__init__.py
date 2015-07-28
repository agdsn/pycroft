# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft
    ~~~~~~~~~~~~~~

    This package contains everything.

    :copyright: (c) 2011 by AG DSN.
"""
from sqlalchemy.orm.exc import NoResultFound
from werkzeug.local import LocalProxy
from pycroft.model.config import Config


def _get_config():
    config = Config.q.get(1)
    if config is None:
        raise NoResultFound
    return config


config = LocalProxy(_get_config, "config")
