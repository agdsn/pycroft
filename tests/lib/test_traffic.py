# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.

from tests import FixtureDataTestBase
from tests.fixtures.dummy.traffic import (TrafficVolumeData, TrafficBalanceData,
                                          TrafficCreditData)
from tests.fixtures.dummy.host import (IPData, UserHostData, UserInterfaceData,
                                       ServerHostData, ServerInterfaceData)
from tests.fixtures.dummy.user import UserData

from pycroft.model import session
from pycroft.model.user import User
from pycroft.lib.user import traffic_balance_expr, traffic_balance


class Test_010_BalanceCalculation(FixtureDataTestBase):
    datasets = [UserData, IPData, UserInterfaceData, UserHostData,
                ServerHostData, ServerInterfaceData,
                TrafficVolumeData, TrafficBalanceData, TrafficCreditData]

    def test_0010_balance_calculation(self):
        # User with multiple ips and multiple hosts
        user = User.q.filter_by(login=UserData.dummy.login).one()
        correct_balance_user = (
            TrafficBalanceData.dummy_balance.amount +
            TrafficCreditData.dummy_credit.amount -
            TrafficVolumeData.dummy_volume_ipv6.amount -
            TrafficVolumeData.dummy_volume_server.amount -
            TrafficVolumeData.dummy_volume.amount)

        self.assertEqual(correct_balance_user, traffic_balance(user))

        self.assertEqual(correct_balance_user,
                         session.session.query(traffic_balance_expr()).filter(
                             User.id == user.id).one().traffic_balance)

        # User with one host and no past balance
        privileged = User.q.filter_by(login=UserData.privileged.login).one()
        correct_balance_priv = (
            -TrafficVolumeData.dummy_volume_switch.amount)
        self.assertEqual(correct_balance_priv, traffic_balance(privileged))
        self.assertEqual(correct_balance_priv,
                         session.session.query(traffic_balance_expr()).filter(
                             User.id == privileged.id).one().traffic_balance)

        # test comparator expression
        correct_values = [(user.id, correct_balance_user>0),
                          (privileged.id, correct_balance_priv>0)]
        res = session.session.query(User.id, traffic_balance_expr()>0).all()

        self.assertEqual(correct_values, res)