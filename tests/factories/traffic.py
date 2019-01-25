# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import factory
from factory.fuzzy import FuzzyInteger, FuzzyChoice

from pycroft.model.traffic import TrafficVolume
from tests.factories import IPFactory
from .base import BaseFactory
from .user import UserFactory


class TrafficDataFactory(BaseFactory):
    class Meta:
        abstract = True

    amount = FuzzyInteger(0, 60 * 1024 ** 3)
    timestamp = factory.Faker('date_time')
    user = factory.SubFactory(UserFactory)


class TrafficVolumeFactory(TrafficDataFactory):
    class Meta:
        model = TrafficVolume

    ip = factory.SubFactory(IPFactory)
    type = FuzzyChoice(['Ingress', 'Egress'])
    packets = FuzzyInteger(0, 5000)
