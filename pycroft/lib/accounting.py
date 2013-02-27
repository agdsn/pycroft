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
from datetime import datetime, timedelta, date, time

from sqlalchemy import func
from pycroft.model import session
from pycroft.model.accounting import TrafficVolume, TrafficCredit
from pycroft.model.host import Host, IP, UserHost
from pycroft.model.user import Membership, Property, TrafficGroup, User


def user_volumes(user):
    """Get a query for all user traffic volumes for the given user.

    :param user: The user to query for.
    :return: The query of the user volumes.
    """
    return TrafficVolume.q.join(
        TrafficVolume.ip
    ).join(
        IP.host
    ).join(
        UserHost.user
    ).filter(
        UserHost.user == user
    )


def traffic_consumption(user, start=None, end=None):
    """Get the summarized traffic usage for a given user within a given interval.

    :param user: The user to query for.
    :param start: The start of the period
    :param end: The end of the period
    :return: The amount of traffic.
    """
    if start is None:
        start = datetime.now()
    if end is None:
        end = start - timedelta(days=1)
    value = session.session.query(
        func.sum(TrafficVolume.size).label("amount")
    ).join(
        TrafficVolume.ip
    ).join(
        IP.host
    ).join(
        UserHost.owner
    ).filter(
        UserHost.owner == user
    ).filter(
        TrafficVolume.timestamp < start
    ).filter(
        TrafficVolume.timestamp > end
    ).one()
    return value.amount


def active_user_credit(user):
    """Get the users credit that is currently active (the newest).

    :param user: The user to get the credit for.
    :return: The TrafficCredit value.
    """
    return TrafficCredit.q.filter(
        TrafficCredit.user == user
    ).order_by(
        TrafficCredit.grant_date.desc()
    ).first()


def _today():
    """Helper to get the datetime from today midnight

    :return: A datetime from the start of the day
    """
    return datetime.combine(date.today(), time())


def users_with_exceeded_traffic():
    """Get a list of all users with exceeded traffic.

    :return: The list of all with exceeded Traffic
    """
    today = _today()
    yesterday = today - timedelta(days=1)

    # used user traffic by user_id
    volume = session.session.query(
        User.id.label("user_id"),
        func.sum(TrafficVolume.size).label("amount")
    ).join(
        TrafficVolume.ip
    ).join(
        IP.host
    ).join(
        UserHost.user
    ).filter(
        TrafficVolume.timestamp < today
    ).filter(
        TrafficVolume.timestamp > yesterday
    ).group_by(User.id).subquery()

    # users without accounting
    unlimited = session.session.query(
        User.id.label("user_id"),
    ).join(
        User.active_property_groups
    ).filter(
        Property.name == "no_traffic_accounting"
    ).subquery()

    # ids of the newest user credit entries
    newest_credits = session.session.query(
        TrafficCredit.user_id.label("user_id"),
        func.max(TrafficCredit.id).label("credit_id")
    ).group_by(
        TrafficCredit.user_id
    ).subquery()

    # the final query
    query = User.q.join(
        (newest_credits, newest_credits.c.user_id == User.id)
    ).join(
        (TrafficCredit, TrafficCredit.id == newest_credits.c.credit_id)
    ).outerjoin(
        (unlimited, unlimited.c.user_id == User.id)
    ).filter(
        unlimited.c.user_id == None
    ).join(
        (volume, volume.c.user_id == User.id)
    ).filter(
        volume.c.amount > 0
    ).filter(
        TrafficCredit.amount > 0
    ).filter(
        volume.c.amount <= TrafficCredit.amount
    )

    return query.all()


def has_exceeded_traffic(user):
    """
    The function calculates the balance of the users traffic.
    :param user: The user object which has to be checked.
    :return: True if the user has more traffic than allowed and false if he
    did not exceed the limit.
    """
    if user.has_property("no_traffic_accounting"):
        return False

    today = _today()
    credit = active_user_credit(user)
    used = traffic_consumption(user, today, today - timedelta(days=1))

    return credit < used
