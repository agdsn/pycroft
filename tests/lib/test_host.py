# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.lib.host import change_mac
from tests import FactoryDataTestBase
from tests.factories import UserFactory, UserWithHostFactory, InterfaceFactory


class ChangeMacTest(FactoryDataTestBase):
    def create_factories(self):
        super().create_factories()
        self.interface = InterfaceFactory.create()
        UserWithHostFactory.create(host__interface=self.interface)
        self.processor = UserFactory.create()

    def test_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        change_mac(self.interface, new_mac, self.processor)
        self.assertEqual(self.interface.mac, new_mac)
