# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.lib.host import change_mac
from pycroft.model import session
from pycroft.model.host import Interface
from pycroft.model.user import User
from pycroft.model.logging import LogEntry
from tests import FixtureDataTestBase
from tests.fixtures.dummy.user import UserData
from tests.fixtures.dummy.host import UserInterfaceData


class Test_005_change_mac_interface(FixtureDataTestBase):
    datasets = [UserInterfaceData, UserData]

    def setUp(self):
        super(Test_005_change_mac_interface, self).setUp()
        self.user = User.q.filter_by(login=UserData.dummy.login).one()

    def test_0010_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        interface = Interface.q.filter_by(
            mac=UserInterfaceData.dummy.mac).one()
        change_mac(interface, new_mac, self.user)
        self.assertEqual(interface.mac, new_mac)
