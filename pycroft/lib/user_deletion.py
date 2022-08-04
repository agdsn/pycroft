"""
pycroft.lib.user_deletion
~~~~~~~~~~~~~~~~~~~~~~~~~

This module contains methods concerning user archival and deletion.
"""
from __future__ import annotations
import typing as t
from datetime import timedelta, datetime
from typing import Protocol, cast
from collections.abc import Sequence

from sqlalchemy import func, and_, not_
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.sql import Select
from sqlalchemy.sql.functions import current_timestamp

from pycroft.model.property import CurrentProperty
from pycroft.model.user import User
from pycroft.lib.membership import select_user_and_last_mem


class ArchivableMemberInfo(Protocol):
    User: User
    mem_id: int
    mem_end: datetime


# mrh, not available in py3.10…
class _WindowArgs[TP, TO](t.TypedDict):
    partition_by: TP
    order_by: TO

def select_archivable_members(delta: timedelta) -> Select:  # Select[Tuple[User, int, datetime]]
    # last_mem: (user_id, mem_id, mem_end)
    last_mem = select_user_and_last_mem().cte("last_mem")
    return (
        select(
            User,
            last_mem.c.mem_id,
            last_mem.c.mem_end,
        )
        .select_from(last_mem)
        # Join the granted `do-not-archive` property, if existent
        .join(CurrentProperty,
              and_(last_mem.c.user_id == CurrentProperty.user_id,
                   CurrentProperty.property_name == 'do-not-archive',
                   not_(CurrentProperty.denied)),
              isouter=True)
        # …and use that to filter out the `do-not-archive` occurrences.
        .filter(CurrentProperty.property_name.is_(None))
        .join(User, User.id == last_mem.c.user_id)
        .filter(last_mem.c.mem_end < current_timestamp() - delta)
        .order_by(last_mem.c.mem_end)

    )


def get_archivable_members(
    session: Session, delta: timedelta = timedelta(days=14)
) -> Sequence[ArchivableMemberInfo]:
    """Return all the users that qualify for being archived right now.

    Selected are those users
    - whose last membership in the member_group ended two weeks in the past,
    - excluding users who currently have the `do-not-archive` property.

    We joined load the following information:
    - hosts
    - account
    - room
    - current_properties_maybe_denied

    :param session:
    :param delta: how far back the end of membership has to lie (positive timedelta).
    """
    return cast(
        list[ArchivableMemberInfo],
        session.execute(
            select_archivable_members(delta)
            .options(
                joinedload(User.hosts),
                # joinedload(User.current_memberships),
                joinedload(User.account, innerjoin=True),
                joinedload(User.room),
                joinedload(User.current_properties_maybe_denied),
            )
        ).unique().all(),
    )


def archive_users(session: Session, user_ids: Sequence[int]) -> None:
    # todo remove hosts
    # todo remove tasks
    # todo remove log entries
    # todo insert these users into an archival log
    # todo add membership in archival group
    pass
