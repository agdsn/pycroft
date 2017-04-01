# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
tests.test_schema
~~~~~~~~~~~~~~

This module contains Tests for the basic model schema

:copyright: (c) 2011 by AG DSN.
"""
import unittest

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
                message = ex.args[0]
                if message.startswith("One or more mappers failed to initialize"):
                    return message
    return None


class Test_010_SchemaMapping(unittest.TestCase):
    def test_0010_mapping_base(self):
        from pycroft.model import base
        msg = try_mapper(base)
        self.assertIsNone(msg, msg)

    def test_0020_mapping_building(self):
        from pycroft.model import facilities
        msg = try_mapper(facilities)
        self.assertIsNone(msg, msg)

    def test_0030_mapping_hosts(self):
        from pycroft.model import host
        msg = try_mapper(host)
        self.assertIsNone(msg, msg)

    def test_0040_mapping_logging(self):
        from pycroft.model import logging
        msg = try_mapper(logging)
        self.assertIsNone(msg, msg)

    def test_0050_mapping_session(self):
        from pycroft.model import session
        msg = try_mapper(session)
        self.assertIsNone(msg, msg)

    def test_0060_mapping_user(self):
        from pycroft.model import user
        msg = try_mapper(user)
        self.assertIsNone(msg, msg)

    def test_0080_mapping_accounting(self):
        from pycroft.model import traffic
        msg = try_mapper(traffic)
        self.assertIsNone(msg, msg)

    def test_0090_mapping_config(self):
        from pycroft.model import config
        msg = try_mapper(config)
        self.assertIsNone(msg, msg)

    def test_0100_mapping_finance(self):
        from pycroft.model import finance
        msg = try_mapper(finance)
        self.assertIsNone(msg, msg)


