# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import datetime, timedelta
import mock
from functools import wraps

from pycroft.lib.accounting import user_volumes, traffic_consumption, \
    active_user_credit
from pycroft.model import session
from pycroft.model.accounting import TrafficVolume
from pycroft.model.host import IP
from pycroft.model.user import User
from tests import FixtureDataTestBase
from tests.fixtures.dummy.host import IPData
from tests.fixtures.dummy.user import UserData


def fix_datetiume_utcnow(module, fixed_date):
    def _datetime_patch(fn):
        @wraps(fn)
        def _decorated(*args, **kwargs):
            with  mock.patch("%s.datetime" % module) as date_mock:
                date_mock.utcnow.return_value = fixed_date
                date_mock.side_effect = lambda *args, **kw: datetime(*args,
                                                                     **kw)
                return fn(*args, **kwargs)

        return _decorated

    return _datetime_patch


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
        self.assertEqual(sum([item.size for item in volumes]), size)

    def test_0020_get_no_traffic_volumes(self):
        volumes = user_volumes(self.user)
        self.assertEqual(volumes.count(), 0)


class Test_020_TrafficConsumption(FixtureDataTestBase):
    datasets = [UserData, IPData, TrafficVolumeData]

    @property
    def _user(self):
        return User.q.get(UserData.traffic_user1.id)

    @fix_datetiume_utcnow("pycroft.lib.accounting",
                          fixture_timebase - timedelta(days=1))
    def test_0010_no_interval(self):
        self.assertEqual(traffic_consumption(self._user),
                         TrafficVolumeData.traffic_volume2.size)

    @fix_datetiume_utcnow("pycroft.lib.accounting",
                          fixture_timebase - timedelta(days=1))
    def test_0020_start_interval(self):
        self.assertEqual(
            traffic_consumption(self._user, start=fixture_timebase),
            TrafficVolumeData.traffic_volume1.size)
        self.assertEqual(
            traffic_consumption(self._user,
                                start=fixture_timebase - timedelta(days=2)),
            TrafficVolumeData.traffic_volume3.size)

    @fix_datetiume_utcnow("pycroft.lib.accounting",
                          fixture_timebase - timedelta(days=1))
    def test_0030_start_end_interval(self):
        self.assertEqual(
            traffic_consumption(self._user,
                                start=fixture_timebase,
                                end=fixture_timebase - timedelta(days=2)),
            sum((volume_size(i) for i in xrange(1, 3))))

    def test_0040_wrong_range(self):
        self.assertRaises(AssertionError, traffic_consumption, self._user,
                          start=fixture_timebase - timedelta(days=1),
                          end=fixture_timebase)


class Test_030_ActiveUserCredit(FixtureDataTestBase):
    datasets = [UserData, IpData, TrafficVolumeData, TrafficCreditData]

    def test_0010_active_credit(self):
        user = User.q.get(UserData.traffic_user1.id)
        self.assertIsNotNone(active_user_credit(user))
        self.assertEqual(active_user_credit(user).id,
                         TrafficCreditData.traffic_credit1.id)

    def test_0020_no_active_credit(self):
        user = User.q.get(UserData.no_traffic_user1.id)
        self.assertIsNone(active_user_credit(user))


class Test_040_UserWithExceededTraffic(FixtureDataTestBase):
    datasets = [UserData, IpData, TrafficVolumeData, TrafficCreditData]

    def test_0010_peng(self):
        self.fail("Implement!")


class Test_050_FindActualTrafficGroup(FixtureDataTestBase):
    datasets = [UserData, IpData, TrafficVolumeData, TrafficCreditData]

    def test_0010_peng(self):
        self.fail("Implement!")


class Test_060_GrantTraffic(FixtureDataTestBase):
    datasets = [UserData, IpData, TrafficVolumeData, TrafficCreditData]

    def test_0010_peng(self):
        self.fail("Implement!")


class Test_070_GrantAllTraffic(FixtureDataTestBase):
    datasets = [UserData, IpData, TrafficVolumeData, TrafficCreditData]

    def test_0010_peng(self):
        self.fail("Implement!")


class Test_070_HasExceededTraffic(FixtureDataTestBase):
    datasets = [UserData, IpData, TrafficVolumeData, TrafficCreditData]

    def test_0010_peng(self):
        self.fail("Implement!")
