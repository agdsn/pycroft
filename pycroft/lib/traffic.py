# Copyright (c) 2017 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.traffic
~~~~~~~~~~~~~~~~~~~

This module contains functions concerning network traffic

"""
import typing as t
from datetime import timedelta

from sqlalchemy import func, select, literal_column, delete, CursorResult
from sqlalchemy.orm import join, Session

from pycroft.model import session
from pycroft.model.traffic import TrafficVolume
from pycroft.model.user import User


class UserTrafficInfo(t.Protocol):
    id: int
    name: str
    traffic_for_days: int


def get_users_with_highest_traffic(days: int, limit: int) -> list[UserTrafficInfo]:
    return t.cast(
        list[UserTrafficInfo],
        session.session.execute(
            select(
                User.id,
                User.name,
                func.sum(TrafficVolume.amount).label("traffic_for_days"),
            )
            .select_from(join(User, TrafficVolume, TrafficVolume.user_id == User.id))
            .where(User.id != 0)
            .where(
                TrafficVolume.timestamp
                >= (session.utcnow() - timedelta(days - 1)).date()
            )
            .group_by(User.id, User.name)
            .order_by(literal_column("traffic_for_days").desc())
            .limit(limit)
        ).fetchall(),
    )


def delete_old_traffic_data(session: Session) -> int:
    week_ago = func.current_timestamp() - timedelta(weeks=1)
    stmt = delete(TrafficVolume).where(TrafficVolume.timestamp < week_ago)
    result = t.cast(CursorResult, session.execute(stmt))
    return result.rowcount
