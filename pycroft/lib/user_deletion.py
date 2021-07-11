from datetime import timedelta

from sqlalchemy import func, nulls_last
from sqlalchemy.engine import Row
from sqlalchemy.future import select
from sqlalchemy.sql.elements import and_, not_
from sqlalchemy.sql.functions import current_timestamp

from pycroft import config, Config
from pycroft.model.property import CurrentProperty
from pycroft.model.session import session
from pycroft.model.user import User, Membership


def get_archivable_members() -> list[Row]:
    """Return all the users that qualify for being archived right now.

    Selected are those users
    - whose last membership in the member_group ended two weeks in the past,
    - excluding users who currently have the `noarchive` property.
    """
    # see FunctionElement.over
    window_args = {'partition_by': User.id, 'order_by': nulls_last(Membership.ends_at),
                   'rows': (None, None)}
    last_mem = (
        select(
            User.id.label('user_id'),
            func.last_value(Membership.id).over(**window_args).label('mem_id'),
            func.last_value(Membership.ends_at).over(**window_args).label('mem_end'),
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
            CurrentProperty.property_name.is_not(None).label('noarchive')
        )
        .select_from(last_mem)
        .join(CurrentProperty,
              and_(last_mem.c.user_id == CurrentProperty.user_id,
                   CurrentProperty.property_name == 'noarchive',
                   not_(CurrentProperty.denied)),
              isouter=True)
        .join(User, User.id == last_mem.c.user_id)
        .filter(last_mem.c.mem_end < current_timestamp() - timedelta(days=14))
        .order_by(last_mem.c.mem_end)
    )

    return session.execute(stmt).all()


def get_invalidated_archive_memberships() -> list[Membership]:
    """Get all memberships in `to_be_archived` of users who have an active `do-not-archive` property.

    This can happen if archivability is detected, and later the user becomes a member again,
    or if for some reason the user shall not be archived.
    """
    pass
