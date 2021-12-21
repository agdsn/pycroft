from datetime import timedelta, datetime
from typing import Protocol, Sequence

from sqlalchemy import func, nulls_last
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.sql.elements import and_, not_, ClauseElement
from sqlalchemy.sql.functions import current_timestamp

from pycroft import Config
from pycroft.model.property import CurrentProperty
from pycroft.model.user import User, Membership


class ArchivableMemberInfo(Protocol):
    User: User
    mem_id: int
    mem_end: datetime


def get_archivable_members(session: Session) -> Sequence[ArchivableMemberInfo]:
    """Return all the users that qualify for being archived right now.

    Selected are those users
    - whose last membership in the member_group ended two weeks in the past,
    - excluding users who currently have the `do-not-archive` property.
    """
    # see FunctionElement.over
    mem_ends_at = func.upper(Membership.active_during)
    window_args: dict[str, ClauseElement | Sequence[ClauseElement | str] | None] = {
        'partition_by': User.id,
        'order_by': nulls_last(mem_ends_at),
    }
    last_mem = (
        select(
            User.id.label('user_id'),
            func.last_value(Membership.id).over(**window_args, rows=(None, None)).label('mem_id'),
            func.last_value(mem_ends_at).over(**window_args, rows=(None, None)).label('mem_end'),
        )
        .select_from(User)
        .distinct()
        .join(Membership)
        .join(Config, Config.member_group_id == Membership.group_id)
    ).cte('last_mem')
    stmt = (
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
        .filter(last_mem.c.mem_end < current_timestamp() - timedelta(days=14))
        .order_by(last_mem.c.mem_end)
        .options(joinedload(User.hosts), joinedload(User.current_memberships),
                 joinedload(User.account), joinedload(User.room),
                 joinedload(User.current_properties_maybe_denied))
    )
    # The default dedupe strategy for the `mem_id` and `mem_end` columns is `id` instead of `hash`.
    # See sqlalchemy#6769
    return session.execute(stmt).unique(lambda row: row).all()


def get_invalidated_archive_memberships() -> list[Membership]:
    """Get all memberships in `to_be_archived` of users who have an active `do-not-archive` property.

    This can happen if archivability is detected, and later the user becomes a member again,
    or if for some reason the user shall not be archived.
    """
    pass
