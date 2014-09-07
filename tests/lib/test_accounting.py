# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime

from pycroft.lib.accounting import user_volumes
from pycroft.model import session
from pycroft.model.accounting import TrafficVolume
from pycroft.model.host import IP
from pycroft.model.user import User
from tests import FixtureDataTestBase
from tests.fixtures.dummy.host import IPData
from tests.fixtures.dummy.user import UserData


class Test_010_UserVolumes(FixtureDataTestBase):
    datasets = (UserData, IPData)

    def setUp(self):
        super(Test_010_UserVolumes, self).setUp()
        self.user = User.q.filter_by(login=UserData.dummy.login).one()

    def test_0010_get_traffic_volumes(self):
        size = 1000
        ip = IP.q.filter_by(address=IPData.dummy_user_ipv4.address).one()
        session.session.add_all((
            TrafficVolume(size=size, timestamp=datetime.utcnow(),
                          ip=ip, traffic_type='IN'),
        ))
        volumes = user_volumes(self.user)
        self.assertEqual(volumes.count(), 1)
        self.assertEqual(volumes.first().size, size)

    def test_0020_get_no_traffic_volumes(self):
        volumes = user_volumes(self.user)
        self.assertEqual(volumes.count(), 0)
