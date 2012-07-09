# -*- coding: utf-8 -*-
"""
tests.test_schema
~~~~~~~~~~~~~~

This module contains Tests for the basic model schema

:copyright: (c) 2011 by AG DSN.
"""

import unittest
from sqlalchemy.orm.util import class_mapper
import sqlalchemy.exc

from tests import OldPythonTestCase


def try_mapper(module):
    for attr in dir(module):
        if attr[0] == '_': continue
        try:
            cls = getattr(module, attr)
            class_mapper(cls)
        except Exception as ex:
            if isinstance(ex, sqlalchemy.exc.InvalidRequestError):
                if ex.message.startswith("One or more mappers failed to initialize"):
                    return ex.message
    return None


class Test_010_SchemaMapping(OldPythonTestCase):
    def test_0010_mapping_base(self):
        from pycroft.model import base
        msg = try_mapper(base)
        self.assertIsNone(msg, msg)

    def test_0020_mapping_dormitory(self):
        from pycroft.model import dormitory
        msg = try_mapper(dormitory)
        self.assertIsNone(msg, msg)

    def test_0030_mapping_hosts(self):
        from pycroft.model import hosts
        msg = try_mapper(hosts)
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

    def test_0070_mapping_properties(self):
        from pycroft.model import properties
        msg = try_mapper(properties)
        self.assertIsNone(msg, msg)

    def test_0080_mapping_accounting(self):
        from pycroft.model import accounting
        msg = try_mapper(accounting)
        self.assertIsNone(msg, msg)

    def test_0090_mapping_ports(self):
        from pycroft.model import ports
        msg = try_mapper(ports)
        self.assertIsNone(msg, msg)

    def test_0100_mapping_finance(self):
        from pycroft.model import finance
        msg = try_mapper(finance)
        self.assertIsNone(msg, msg)


