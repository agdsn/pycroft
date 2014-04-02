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

from sqlalchemy import func, and_
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

    assert start > end

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
        TrafficVolume.timestamp <= start
    ).filter(
        TrafficVolume.timestamp > end
    ).one()
    return value.amount


def active_user_credit(user):
    """Get the users credit that is currently active (the newest).

    :param user: The user to get the credit for.
    :return: The TrafficCredit value.
    :rtype: TrafficCredit
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


def _traffic_by_userid(today, yesterday):
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
    return volume


def _unaccounted_by_userid():
    unlimited = session.session.query(
        User.id.label("user_id"),
    ).join(
        User.active_property_groups
    ).filter(
        Property.name == "no_traffic_accounting"
    ).subquery()
    return unlimited


def _latest_credits_by_userid():
    newest_credits = session.session.query(
        TrafficCredit.user_id.label("user_id"),
        func.max(TrafficCredit.id).label("credit_id")
    ).group_by(
        TrafficCredit.user_id
    ).subquery()
    return newest_credits


def users_with_exceeded_traffic():
    """Get a list of all users with exceeded traffic.

    :return: The list of all with exceeded Traffic
    """
    today = _today()
    yesterday = today - timedelta(days=1)

    # used user traffic by user_id
    volume = _traffic_by_userid(today, yesterday)

    # users without accounting
    unlimited = _unaccounted_by_userid()

    # ids of the newest user credit entries
    newest_credits = _latest_credits_by_userid()

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


def find_actual_trafficgroup(user):
    """Get the current relevant traffic group for a given user.

    relevant means, its active and it is the one with the most
    recent start_date.

    :param user: The user to query for.
    :return: The assigned TrafficGroup.
    :rtype: TrafficGroup
    """
    return session.session.query(
        TrafficGroup
    ).join(
        TrafficGroup.memberships
    ).join(
        Membership.user
    ).filter(
        User.id == user.id
    ).filter(
        Membership.active()
    ).order_by(
        Membership.begins_at.desc()
    ).first()


def _traffic_groups_by_userid():
    start_dates = session.session.query(
        User.id.label("user_id"),
        func.max(Membership.start_date).label("start_date")
    ).join(
        (Membership, and_(Membership.user_id == User.id,
                          Membership.active))
    ).join(
        (TrafficGroup, TrafficGroup.id == Membership.group_id)
    ).group_by(
        User.id
    ).subquery()

    return session.session.query(
        User.id.label("user_id"),
        func.max(TrafficGroup.id).label("group_id")
    ).join(
        (start_dates, start_dates.c.user_id == User.id)
    ).join(
        (Membership, and_(Membership.user_id == User.id,
                          Membership.active,
                          Membership.start_date == start_dates.c.start_date))
    ).join(
        (TrafficGroup, TrafficGroup.id == Membership.group_id)
    ).group_by(
        User.id
    ).subquery()


def grant_traffic(user, initial_credit=False):
    traffic_group = find_actual_trafficgroup(user)
    assert traffic_group is not None

    now = datetime.now()
    new_credit = TrafficCredit(user=user,
                               grant_date=now,
                               amount=traffic_group.grant_amount * 7,
                               added_amount=traffic_group.grant_amount * 7)

    if not initial_credit:
        active_credit = active_user_credit(user)
        assert active_credit is not None

        consumption = traffic_consumption(user, now, now - timedelta(days=1))

        real_credit = active_credit.amount - consumption
        new_credit.amount = min(real_credit + traffic_group.grant_amount,
                                traffic_group.saving_amount)

        new_credit.added_amount = new_credit.amount - real_credit

    session.session.add(new_credit)
    session.session.commit()


def grant_all_traffic():
    today = _today()
    yesterday = today - timedelta(days=1)

    # used user traffic by user_id
    volume = _traffic_by_userid(today, yesterday)

    # users without accounting
    unlimited = _unaccounted_by_userid()

    # ids of the newest user credit entries
    newest_credits = _latest_credits_by_userid()

    traffic_group_ids = _traffic_groups_by_userid()

    query = session.session.query(User.id.label("user_id"),
                                  func.min(TrafficGroup.saving_amount,
                                           (TrafficCredit.amount -
                                            func.coalesce(volume.c.amount, 0)
                                           ) + TrafficGroup.grant_amount
                                  ).label("new_amount"),
                                  (TrafficCredit.amount -
                                   func.coalesce(volume.c.amount, 0)
                                  ).label("old_amount")
    ).outerjoin(
        (volume, volume.c.user_id == User.id)
    ).outerjoin(
        (unlimited, unlimited.c.user_id == User.id)
    ).join(
        (newest_credits, newest_credits.c.user_id == User.id)
    ).join(
        TrafficCredit, TrafficCredit.id == newest_credits.c.credit_id
    ).join(
        (traffic_group_ids, traffic_group_ids.c.user_id == User.id)
    ).join(
        (TrafficGroup, TrafficGroup.id == traffic_group_ids.c.group_id)
    )

    now = datetime.now()

    new_credits = []
    for entry in query:
        new_credit = TrafficCredit(user_id=entry.user_id,
                                   grant_date=now,
                                   amount=entry.new_amount,
                                   added_amount=entry.new_amount - entry.old_amount)
        new_credits.append(new_credit)

    session.session.add_all(new_credits)
    session.session.commit()


def has_exceeded_traffic(user):
    """
    The function calculates the balance of the users traffic.
    :param user: The user object which has to be checked.
    :return: True if the user has more traffic than allowed and false if he did not exceed the limit.
    """
    if user.has_property("no_traffic_accounting"):
        return False

    today = _today()
    credit = active_user_credit(user)
    used = traffic_consumption(user, today, today - timedelta(days=1))

    return credit < used
