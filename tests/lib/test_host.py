# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.lib.host import change_mac
from pycroft.model import session
from pycroft.model.host import UserNetDevice
from pycroft.model.user import User
from pycroft.model.logging import LogEntry
from tests import FixtureDataTestBase
from tests.fixtures.dummy.user import UserData
from tests.fixtures.dummy.host import UserNetDeviceData


class Test_005_change_mac_net_device(FixtureDataTestBase):
    datasets = [UserNetDeviceData, UserData]

    def setUp(self):
        super(Test_005_change_mac_net_device, self).setUp()
        self.user = User.q.filter_by(login=UserData.dummy.login).one()

    def tearDown(self):
        LogEntry.q.delete()
        session.session.commit()
        super(Test_005_change_mac_net_device, self).tearDown()

    def test_0010_change_mac(self):
        new_mac = "20:00:00:00:00:00"
        netdev = UserNetDevice.q.filter_by(
            mac=UserNetDeviceData.dummy_device.mac).one()
        change_mac(netdev, new_mac, self.user)
        self.assertEqual(netdev.mac, new_mac)
