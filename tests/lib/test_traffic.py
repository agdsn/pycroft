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

    def setUp(self):
        super(Test_010_BalanceCalculation, self).setUp()
        self.users = [# User with multiple ips and multiple hosts:
                      User.q.filter_by(login=UserData.dummy.login).one(),

                      # User with one host and no past balance
                      User.q.filter_by(login=UserData.privileged.login).one(),

                      # User with balance timestamp in future
                      User.q.filter_by(login=UserData.anotheruser.login).one()]
        self.correct_balance = {
            self.users[0]: (
                TrafficBalanceData.dummy_balance.amount +
                TrafficCreditData.dummy_credit.amount -
                TrafficVolumeData.dummy_volume_ipv6.amount -
                TrafficVolumeData.dummy_volume_server.amount -
                TrafficVolumeData.dummy_volume.amount),
            self.users[1]: (-TrafficVolumeData.dummy_volume_switch.amount),
            self.users[2]: None,
        }

    def test_0010_orm(self):
        orm_values = map(lambda u: (u.id, traffic_balance(u)), self.users)
        correct_values = map(lambda (u, b): (u.id, b),
                             self.correct_balance.items())
        self.assertEqual(set(orm_values), set(correct_values))

    def test_0010_expr(self):
        expr_values = session.session.query(
            User.id, traffic_balance_expr()).all()
        correct_values = map(lambda (u, b): (u.id, b),
                             self.correct_balance.items())
        self.assertEqual(set(expr_values), set(correct_values))

    def test_0030_expr_comparator(self):
        # test comparator expression
        correct_values = map(lambda (u, b): (u.id, b > 0
                                                   if b is not None else None),
                             self.correct_balance.items())
        res = session.session.query(User.id, traffic_balance_expr()>0).all()

        self.assertEqual(set(correct_values), set(res))

