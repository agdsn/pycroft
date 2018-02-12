# -*- coding: utf-8 -*-
# Copyright (c) 2016 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from datetime import timedelta
import factory

from pycroft.model.user import TrafficGroup

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
