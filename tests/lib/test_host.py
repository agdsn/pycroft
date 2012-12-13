# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
__author__ = 'l3nkz'

from tests import FixtureDataTestBase
from tests.lib.fixtures.host_fixtures import UserNetDeviceData, UserData

from pycroft.lib.hosts import change_mac

from pycroft.model import session
from pycroft.model.hosts import UserNetDevice
from pycroft.model.user import User
from pycroft.model.logging import LogEntry

class Test_030_change_mac_net_device(FixtureDataTestBase):
    datasets = [UserNetDeviceData, UserData]

    def tearDown(self):
        LogEntry.q.delete()
        session.session.commit()
        super(Test_030_change_mac_net_device, self).tearDown()

    def test_0010_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        netdev = UserNetDevice.q.get(UserNetDeviceData.dummy_device1.id)
        user = User.q.get(UserData.dummy_user1.id)
        change_mac(netdev, new_mac, user)
        self.assertEqual(netdev.mac, new_mac)

