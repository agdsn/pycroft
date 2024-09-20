import typing as t
from datetime import date

from sqlalchemy import select, ColumnElement, Boolean, String

from pycroft import property
from pycroft.helpers.utc import DateTimeTz
from pycroft.model import session
from pycroft.model.task import TaskStatus, TaskType, UserTask
from pycroft.model.traffic import TrafficHistoryEntry
from pycroft.model.traffic import traffic_history as func_traffic_history
from pycroft.model.user import (
    User,
)
from pycroft.lib.finance import user_has_paid


class UserStatus(t.NamedTuple):
    member: bool
    traffic_exceeded: bool
    network_access: bool
    wifi_access: bool
    account_balanced: bool
    violation: bool
    ldap: bool
    admin: bool


def status(user: User) -> UserStatus:
    has_interface = any(h.interfaces for h in user.hosts)
    has_access = user.has_property("network_access")
    return UserStatus(
        member=user.has_property("member"),
        traffic_exceeded=user.has_property("traffic_limit_exceeded"),
        network_access=has_access and has_interface,
        wifi_access=user.has_wifi_access and has_access,
        account_balanced=user_has_paid(user),
        violation=user.has_property("violation"),
        ldap=user.has_property("ldap"),
        admin=any(prop in user.current_properties for prop in _admin_properties),
    )


_admin_properties = property.property_categories["Nutzerverwaltung"].keys()


def traffic_history(
    user_id: int,
    start: DateTimeTz | ColumnElement[DateTimeTz],
    end: DateTimeTz | ColumnElement[DateTimeTz],
) -> list[TrafficHistoryEntry]:
    result = session.session.execute(
        select("*").select_from(func_traffic_history(user_id, start, end))
    ).fetchall()
    return [TrafficHistoryEntry(**row._asdict()) for row in result]


def scheduled_membership_start(user: User) -> date | None:
    """
    :return: The due date of the task that will begin a membership; None if not
             existent
    """
    if (task := membership_beginning_task(user)) is None:
        return None
    return task.due.date()


def scheduled_membership_end(user: User) -> date | None:
    """
    :return: The due date of the task that will end the membership; None if not
             existent
    """
    if (task := membership_ending_task(user)) is None:
        return None
    return task.due.date()


def membership_beginning_task(user: User) -> UserTask:
    """
    :return: Next task that will end the membership of the user
    """

    return t.cast(
        UserTask,
        UserTask.q.filter_by(user_id=user.id, status=TaskStatus.OPEN, type=TaskType.USER_MOVE_IN)
        .filter(UserTask.parameters_json["begin_membership"].cast(Boolean))
        .order_by(UserTask.due.asc())
        .first(),
    )


def membership_ending_task(user: User) -> UserTask:
    """
    :return: Next task that will end the membership of the user
    """

    return t.cast(
        UserTask,
        UserTask.q.filter_by(user_id=user.id, status=TaskStatus.OPEN, type=TaskType.USER_MOVE_OUT)
        # Casting jsonb -> bool directly is only supported since PG v11
        .filter(UserTask.parameters_json["end_membership"].cast(String).cast(Boolean))
        .order_by(UserTask.due.asc())
        .first(),
    )
