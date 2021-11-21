# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
tests.test_schema
~~~~~~~~~~~~~~

This module contains Tests for the basic model schema

:copyright: (c) 2011 by AG DSN.
"""
from sqlalchemy.orm.util import class_mapper
import sqlalchemy.exc


def try_mapper(module):
    for attr in dir(module):
        if attr[0] == '_': continue
        try:
            cls = getattr(module, attr)
            class_mapper(cls)
        except Exception as ex:
            if isinstance(ex, sqlalchemy.exc.InvalidRequestError):
                message = str(ex)
                if message.startswith("One or more mappers failed to initialize"):
                    return message
    return None


def test_mapping_base():
    from pycroft.model import base
    msg = try_mapper(base)
    assert msg is None, msg

def test_mapping_building():
    from pycroft.model import facilities
    msg = try_mapper(facilities)
    assert msg is None, msg

def test_mapping_hosts():
    from pycroft.model import host
    msg = try_mapper(host)
    assert msg is None, msg

def test_mapping_logging():
    from pycroft.model import logging
    msg = try_mapper(logging)
    assert msg is None, msg

def test_mapping_session():
    from pycroft.model import session
    msg = try_mapper(session)
    assert msg is None, msg

def test_mapping_user():
    from pycroft.model import user
    msg = try_mapper(user)
    assert msg is None, msg

def test_mapping_accounting():
    from pycroft.model import traffic
    msg = try_mapper(traffic)
    assert msg is None, msg

def test_mapping_config():
    from pycroft.model import config
    msg = try_mapper(config)
    assert msg is None, msg

def test_mapping_finance():
    from pycroft.model import finance
    msg = try_mapper(finance)
    assert msg is None, msg
