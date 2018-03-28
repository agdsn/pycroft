# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta
import factory
from factory.fuzzy import FuzzyInteger, FuzzyChoice

from pycroft.model.traffic import TrafficCredit, TrafficVolume, TrafficBalance
from pycroft.model.user import TrafficGroup
from tests.factories import IPFactory

from .base import BaseFactory
from .user import UserFactory


class TrafficGroupFactory(BaseFactory):
    class Meta:
        model = TrafficGroup

    name = factory.Sequence(lambda n: "traffic_group_{}".format(n))
    credit_limit = 63*2**30
    credit_amount = 3*2**30
    credit_interval = timedelta(days=1)
    initial_credit_amount = 21*2**30


class TrafficDataFactory(BaseFactory):
    class Meta:
        abstract = True

    amount = FuzzyInteger(0, 60 * 1024 ** 3)
    timestamp = factory.Faker('date_time')
    user = factory.SubFactory(UserFactory)


class TrafficCreditFactory(TrafficDataFactory):
    class Meta:
        model = TrafficCredit


class TrafficVolumeFactory(TrafficDataFactory):
    class Meta:
        model = TrafficVolume

    ip = factory.SubFactory(IPFactory)
    type = FuzzyChoice(['Ingress', 'Egress'])
    packets = FuzzyInteger(0, 5000)


class TrafficBalanceFactory(TrafficDataFactory):
    class Meta:
        model = TrafficBalance
