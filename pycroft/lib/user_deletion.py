"""
pycroft.lib.user_deletion
~~~~~~~~~~~~~~~~~~~~~~~~~

This module contains methods concerning user archival and deletion.
"""
from __future__ import annotations
import typing as t
from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, cast

from sqlalchemy import func, and_, not_
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.sql import Select

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


def select_archivable_members(
    current_year: int,
) -> Select[tuple[User, int, datetime]]:
    # last_mem: (user_id, mem_id, mem_end)
    last_mem = select_user_and_last_mem().cte("last_mem")
    return (
        select()
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
        .filter(func.extract("year", last_mem.c.mem_end) + 2 <= current_year)
        .order_by(last_mem.c.mem_end)
        .with_only_columns(
            User,
            last_mem.c.mem_id,
            last_mem.c.mem_end,
        )
    )


def get_archivable_members(
    session: Session,
    current_year: int | None = None,
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
    :param current_year: dependency injection of the current year.
        defaults to the current year.
    """
    return cast(
        list[ArchivableMemberInfo],
        session.execute(
            select_archivable_members(
                # I know we're sloppy with time zones,
                # but ±2h around new year's eve don't matter.
                current_year=current_year
                or datetime.now().year
            ).options(
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
