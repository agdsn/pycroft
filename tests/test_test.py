# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from tests import FactoryDataTestBase
from tests.factories.dummy.base import UserFactory


class TestTest(FactoryDataTestBase):
    def setUp(self):
        super(FactoryDataTestBase, self).setUp()

    def test_user_initialized(self):
        user = UserFactory()
        self.assertTrue(user)
