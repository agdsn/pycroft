# -*- coding: utf-8 -*-
# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.traffic
~~~~~~~~~~~~~~~~~~~

This module contains functions concerning network traffic

"""
from sqlalchemy import func

from pycroft.model.traffic import TrafficVolume
from pycroft.model.user import User


def get_users_with_highest_traffic(limit):
    return User.q.join(TrafficVolume).order_by(func.sum(TrafficVolume.amount)).desc().limit(limit).all()
