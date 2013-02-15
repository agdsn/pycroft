# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.accounting
~~~~~~~~~~~~~~

This module contains.

:copyright: (c) 2012 by AG DSN.
"""
from sqlalchemy import func
from pycroft.model import session
from pycroft.model.accounting import TrafficVolume
from pycroft.model.host import Host, IP
from pycroft.model.user import TrafficGroup, User


def has_exceeded_traffic(user):
    """
    The function calculates the balance of the users traffic.
    :param user: The user object which has to be checked.
    :return: True if the user has more traffic than allowed and false if he
    did not exceed the limit.
    """
    result = session.session.query(User.id,
        (func.max(TrafficGroup.traffic_limit) * 1.10) < func.sum(
            TrafficVolume.size).label("has_exceeded_traffic")).join(
        User.active_traffic_groups).join(User.user_host).join(Host.ips).join(
        IP.traffic_volumes).filter(User.id == user.id).group_by(User.id).first()
    if result is not None:
        return result.has_exceeded_traffic
    else: return False
