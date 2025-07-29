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

from sqlalchemy import CTE, ScalarResult, func, and_, not_
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, Session
from sqlalchemy.sql import Select

from pycroft.helpers.i18n.deferred import deferred_gettext
from pycroft.lib.logging import log_user_event
from pycroft.model.host import Host
from pycroft.model.property import CurrentProperty
from pycroft.model.scrubbing import ScrubLog
from pycroft.model.user import RoomHistoryEntry, User
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
    years_following_eom: int,
) -> tuple[Select[tuple[User, int, datetime]], CTE]:
    """Get all members whose year(end of last membership) + 1 + years_following_eom <= current year.

    legal grounds:

    .. epigraph::

       The following data can be collected and processed until the end of
       the next calendar year after membership ends: […]

       -- Privacy policy §2

    :returns: a tuple of statement and the `last_mem` CTE which can be
        reused for late injection of an `order_by`.
    """
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
        .filter(func.extract("year", last_mem.c.mem_end) + 1 + years_following_eom <= current_year)
        .with_only_columns(
            User,
            last_mem.c.mem_id,
            last_mem.c.mem_end,
        )
    ), last_mem


def get_archivable_members(
    session: Session,
    current_year: int | None = None,
    years_following_eom: int | None = None,
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
    :param years_following_eom: dependency injection of the current year.
        defaults to the current year.
    """
    stmt, last_mem = select_archivable_members(
        # I know we're sloppy with time zones,
        # but ±2h around new year's eve don't matter.
        current_year=current_year or datetime.now().year,
        years_following_eom=years_following_eom or 1,
    )
    return cast(
        list[ArchivableMemberInfo],
        session.execute(
            stmt.options(
                joinedload(User.hosts),
                # joinedload(User.current_memberships),
                joinedload(User.account, innerjoin=True),
                joinedload(User.room),
                joinedload(User.current_properties_maybe_denied),
            ).order_by(last_mem.c.mem_end.asc())
        )
        .unique()
        .all(),
    )


def scrubbable_mails_stmt(year: int) -> Select[tuple[User]]:
    """Users whose mails can be scrubbed

    Definition:

    .. epigraph::

       Other e-mail addresses you provide, which are used for contacting you.

       -- Privacy policy §2.6

    :returns: a tuple of statement and the `last_mem` CTE which can be
        reused for late injection of an `order_by`.
    """
    stmt, _ = select_archivable_members(current_year=year, years_following_eom=1)

    return stmt.filter(User.email.is_not(None)).with_only_columns(User).distinct()


def scrubbable_mails(session: Session) -> ScalarResult[User]:
    year = datetime.now().year
    stmt = scrubbable_mails_stmt(year)
    return session.execute(stmt).unique().scalars()


def scrubbable_mails_count(session: Session, year: int) -> int | None:
    stmt = scrubbable_mails_stmt(year)
    return session.scalar(stmt.with_only_columns(func.count()))


# TODO turn into bulk method
def scrub_mail(session: Session, user: User, author: User):
    user.email = None
    session.add(user)
    # two log entries: a user log entry for the support crew,
    # and a system log entry to ensure traceability of all scrubings
    le = log_user_event(
        deferred_gettext("Scrubbed mail address").to_json(), author=author, user=user
    )
    session.add(le)
    session.add(ScrubLog(scrubber="mail", info={"user_id": user.id}))


def scrubbable_hosts_stmt(year: int) -> Select[tuple[Host]]:
    """All the hosts we can delete.

    Deleting them will delete interfaces and assigned IPs by cascade.

    Definition:

    .. epigraph::

       Your MAC and IP addresses, which are required to access the student network.

       -- Privacy policy §2.8
    """
    stmt, _ = select_archivable_members(current_year=year, years_following_eom=1)
    return stmt.join(Host).with_only_columns(Host).distinct()


def scrubbable_dates_of_birth_stmt(year: int) -> Select[tuple[User]]:
    """All the users whose date of birth we can delete.

    Definition:

    .. epigraph::

       Your date of birth, which is required based on TKG §172.

       -- Privacy policy §2.9

    """
    stmt, _ = select_archivable_members(current_year=year, years_following_eom=1)
    return stmt.filter(User.birthdate.is_not(None)).with_only_columns(User).distinct()


def scrubbable_swdd_person_ids(year: int) -> Select[tuple[User]]:
    """All the user whose ``swdd_person_id`` (“Debitorennummer”) we can delete

    .. epigraph::

       If available, your “Debitorennummer” of the Studentenwerk
       Dresden to get information about the rental object (room)
       and the rental period

       -- Privacy policy §2.10

    """
    stmt, _ = select_archivable_members(current_year=year, years_following_eom=1)
    return stmt.filter(User.swdd_person_id.is_not(None)).with_only_columns(User).distinct()


def scrubbable_room_history_entries(year: int) -> Select[tuple[RoomHistoryEntry]]:
    """All the room history entries we can delete

    .. epigraph::

        Past residences in dormitories we are operating in to correctly book membership fees.

        -- Privacy policy §2.11
    """
    ...
    stmt, _ = select_archivable_members(current_year=year, years_following_eom=1)
    return stmt.join(User.room_history_entries).with_only_columns(RoomHistoryEntry).distinct()
