# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.user
~~~~~~~~~~~~~~~~

This module contains.

:copyright: (c) 2012 by AG DSN.
"""
import os
import typing as t
from datetime import date

from sqlalchemy import exists, select, Boolean, String, ColumnElement
from sqlalchemy.orm import Session

from pycroft import config, property
from pycroft.helpers import user as user_helper
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import closed, Interval, starting_from
from pycroft.helpers.user import generate_random_str, login_hash
from pycroft.helpers.utc import DateTimeTz
from pycroft.lib.facilities import get_room
from pycroft.lib.finance import user_has_paid
from pycroft.lib.logging import log_user_event
from pycroft.lib.mail import (
    UserCreatedTemplate,
    UserMovedInTemplate,
    UserResetPasswordTemplate,
)
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.lib.net import get_free_ip, MacExistsException, \
    get_subnets_for_room
from pycroft.lib.task import schedule_user_task
from pycroft.model import session
from pycroft.model.address import Address
from pycroft.model.facilities import Room
from pycroft.model.finance import Account
from pycroft.model.host import IP, Host, Interface
from pycroft.model.session import with_transaction
from pycroft.model.task import TaskType, UserTask, TaskStatus
from pycroft.model.task_serialization import UserMoveParams, UserMoveOutParams, \
    UserMoveInParams
from pycroft.model.traffic import TrafficHistoryEntry
from pycroft.model.traffic import traffic_history as func_traffic_history
from pycroft.model.user import (
    User,
    PropertyGroup,
)
from pycroft.model.unix_account import UnixAccount, UnixTombstone

from .exc import LoginTakenException
from .passwords import generate_wifi_password
from .mail import user_send_mail, send_confirmation_email


password_reset_url = os.getenv('PASSWORD_RESET_URL')


def setup_ipv4_networking(host: Host) -> None:
    """Add suitable ips for every interface of a host"""
    subnets = get_subnets_for_room(host.room)

    for interface in host.interfaces:
        ip_address, subnet = get_free_ip(subnets)
        new_ip = IP(interface=interface, address=ip_address,
                    subnet=subnet)
        session.session.add(new_ip)


def create_user(
    name: str, login: str, email: str, birthdate: date,
    groups: t.Iterable[PropertyGroup], processor: User | None, address: Address,
    passwd_hash: str = None,
    send_confirm_mail: bool = False
) -> tuple[User, str]:
    """Create a new member

    Create a new user with a generated password, finance- and unix account, and make him member
    of the `config.member_group` and `config.network_access_group`.

    :param name: The full name of the user (e.g. Max Mustermann)
    :param login: The unix login for the user
    :param email: E-Mail address of the user
    :param birthdate: Date of birth
    :param groups: The initial groups of the new user
    :param processor: The processor
    :param address: Where the user lives. May or may not come from a room.
    :param passwd_hash: Use password hash instead of generating a new password
    :param send_confirm_mail: If a confirmation mail should be send to the user
    :return:

    :raises LoginTakenException: if the login is used or has been used in the past
    """

    now = session.utcnow()

    if not login_available(login, session.session):
        raise LoginTakenException(login)

    plain_password: str | None = user_helper.generate_password(12)
    # create a new user
    new_user = User(
        login=login,
        name=name,
        email=email,
        registered_at=now,
        account=Account(name="", type="USER_ASSET"),
        password=plain_password,
        wifi_password=generate_wifi_password(),
        birthdate=birthdate,
        address=address
    )

    processor = processor if processor is not None else new_user

    if passwd_hash:
        new_user.passwd_hash = passwd_hash
        plain_password = None

    account = UnixAccount(home_directory=f"/home/{login}")
    new_user.unix_account = account

    with session.session.begin_nested():
        session.session.add(new_user)
        session.session.add(account)
    new_user.account.name = deferred_gettext("User {id}").format(
        id=new_user.id).to_json()

    for group in groups:
        make_member_of(new_user, group, processor, closed(now, None))

    log_user_event(author=processor,
                   message=deferred_gettext("User created.").to_json(),
                   user=new_user)

    user_send_mail(new_user, UserCreatedTemplate(), True)

    if email is not None and send_confirm_mail:
        send_confirmation_email(new_user)

    return new_user, plain_password


def login_available(login: str, session: Session) -> bool:
    """Check whether there is a tombstone with the hash of the given login"""
    hash = login_hash(login)
    stmt = select(
        ~exists(
            select()
            .select_from(UnixTombstone)
            .filter(UnixTombstone.login_hash == hash)
            .add_columns(1)
        )
    )
    return session.scalar(stmt)


@with_transaction
def move_in(
    user: User,
    building_id: int, level: int, room_number: str,
    mac: str | None,
    processor: User | None = None,
    birthdate: date = None,
    host_annex: bool = False,
    begin_membership: bool = True,
    when: DateTimeTz | None = None,
) -> User | UserTask:
    """Move in a user in a given room and do some initialization.

    The user is given a new Host with an interface of the given mac,
    a finance Account, and is made member of important groups.
    Networking is set up.

    Preconditions
    ~~~~~~~~~~~~~

    - User has a unix account.

    :param user: The user to move in
    :param building_id:
    :param level:
    :param room_number:
    :param mac: The mac address of the users pc.
    :param processor:
    :param birthdate: Date of birth
    :param host_annex: when true: if MAC already in use,
        annex host to new user
    :param begin_membership: Starts a membership if true
    :param when: The date at which the user should be moved in

    :return: The user object.
    """

    if when and when > session.utcnow():
        task_params = UserMoveInParams(
            building_id=building_id, level=level, room_number=room_number,
            mac=mac, birthdate=birthdate,
            host_annex=host_annex, begin_membership=begin_membership
        )
        return schedule_user_task(task_type=TaskType.USER_MOVE_IN,
                                  due=when,
                                  user=user,
                                  parameters=task_params,
                                  processor=processor)
    if user.room is not None:
        raise ValueError("user is already living in a room.")

    room = get_room(building_id, level, room_number)

    if birthdate:
        user.birthdate = birthdate

    if begin_membership:
        for group in {config.external_group, config.pre_member_group}:
            if user.member_of(group):
                remove_member_of(
                    user, group, processor, starting_from(session.utcnow())
                )

        for group in {config.member_group, config.network_access_group}:
            if not user.member_of(group):
                make_member_of(user, group, processor, closed(session.utcnow(), None))

    if room:
        user.room = room
        user.address = room.address

        if mac and user.birthdate:
            interface_existing = Interface.q.filter_by(mac=mac).first()

            if interface_existing is not None:
                if host_annex:
                    host_existing = interface_existing.host
                    host_existing.owner_id = user.id

                    session.session.add(host_existing)
                    migrate_user_host(host_existing, user.room, processor)
                else:
                    raise MacExistsException
            else:
                new_host = Host(owner=user, room=room)
                session.session.add(new_host)
                session.session.add(Interface(mac=mac, host=new_host))
                setup_ipv4_networking(new_host)

    user_send_mail(user, UserMovedInTemplate(), True)

    msg = deferred_gettext("Moved in: {room}")

    log_user_event(author=processor if processor is not None else user,
                   message=msg.format(room=room.short_name).to_json(),
                   user=user)

    return user


def migrate_user_host(host: Host, new_room: Room, processor: User) -> None:
    """
    Migrate a UserHost to a new room and if necessary to a new subnet.
    If the host changes subnet, it will get a new IP address.

    :param host: Host to be migrated
    :param new_room: new room of the host
    :param processor: User processing the migration
    :return:
    """
    old_room = host.room
    host.room = new_room

    subnets_old = get_subnets_for_room(old_room)
    subnets = get_subnets_for_room(new_room)

    if subnets_old != subnets:
        for interface in host.interfaces:
            old_ips = tuple(ip for ip in interface.ips)
            for old_ip in old_ips:
                ip_address, subnet = get_free_ip(subnets)
                new_ip = IP(interface=interface, address=ip_address, subnet=subnet)
                session.session.add(new_ip)

                old_address = old_ip.address
                session.session.delete(old_ip)

                message = deferred_gettext("Changed IP of {mac} from {old_ip} to {new_ip}.").format(
                    old_ip=str(old_address), new_ip=str(new_ip.address), mac=interface.mac)
                log_user_event(author=processor, user=host.owner,
                               message=message.to_json())

    message = (
        deferred_gettext("Moved host '{name}' from {room_old} to {room_new}.")
        .format(
            name=host.name, room_old=old_room.short_name, room_new=new_room.short_name
        )
    )

    log_user_event(author=processor,
                   user=host.owner,
                   message=message.to_json())


#TODO ensure serializability
def move(
    user: User,
    building_id: int,
    level: int,
    room_number: str,
    processor: User,
    comment: str | None = None,
    when: DateTimeTz | None = None,
) -> User | UserTask:
    """Moves the user into another room.

    :param user: The user to be moved.
    :param building_id: The id of the building.
    :param level: The level of the new room.
    :param room_number: The number of the new room.
    :param processor: The user initiating this process.  Becomes author of the log message.
        Not used if execution is deferred!
    :param comment: a comment to be included in the log message.
    :param when: The date at which the user should be moved

    :return: The user object of the moved user.
    """

    if when and when > session.utcnow():
        task_params = UserMoveParams(
            building_id=building_id, level=level, room_number=room_number,
            comment=comment
        )
        return schedule_user_task(task_type=TaskType.USER_MOVE,
                                  due=when,
                                  user=user,
                                  parameters=task_params,
                                  processor=processor)

    old_room = user.room
    had_custom_address = user.has_custom_address
    new_room = Room.q.filter_by(
        number=room_number,
        level=level,
        building_id=building_id
    ).one()

    assert old_room != new_room,\
        "A User is only allowed to move in a different room!"

    user.room = new_room
    if not had_custom_address:
        user.address = new_room.address

    args = {'old_room': str(old_room), 'new_room': str(new_room)}
    if comment:
        message = deferred_gettext("Moved from {old_room} to {new_room}.\n"
                                   "Comment: {comment}")
        args.update(comment=comment)
    else:
        message = deferred_gettext("Moved from {old_room} to {new_room}.")

    log_user_event(
        author=processor,
        message=message.format(**args).to_json(),
        user=user
    )

    for user_host in user.hosts:
        if user_host.room == old_room:
            migrate_user_host(user_host, new_room, processor)

    user_send_mail(user, UserMovedInTemplate(), True)

    return user


def traffic_history(
    user_id: int,
    start: DateTimeTz | ColumnElement[DateTimeTz],
    end: DateTimeTz | ColumnElement[DateTimeTz],
) -> list[TrafficHistoryEntry]:
    result = session.session.execute(
        select("*")
        .select_from(func_traffic_history(user_id, start, end))
    ).fetchall()
    return [TrafficHistoryEntry(**row._asdict()) for row in result]


def has_balance_of_at_least(user: User, amount: int) -> bool:
    """Check whether the given user's balance is at least the given
    amount.

    If a user does not have an account, we treat his balance as if it
    were exactly zero.

    :param user: The user we are interested in.
    :param amount: The amount we want to check for.
    :return: True if and only if the user's balance is at least the given
        amount (and False otherwise).
    """
    balance = t.cast(int, user.account.balance if user.account else 0)
    return balance >= amount


def has_positive_balance(user: User) -> bool:
    """Check whether the given user's balance is (weakly) positive.

    :param user: The user we are interested in.
    :return: True if and only if the user's balance is at least zero.
    """
    return has_balance_of_at_least(user, 0)


def get_blocked_groups() -> list[PropertyGroup]:
    return [config.violation_group, config.payment_in_default_group,
                      config.blocked_group]


@with_transaction
def block(
    user: User,
    reason: str,
    processor: User,
    during: Interval[DateTimeTz] = None,
    violation: bool = True,
) -> User:
    """Suspend a user during a given interval.

    The user is added to violation_group or blocked_group in a given
    interval.  A reason needs to be provided.

    :param user: The user to be suspended.
    :param reason: The reason for suspending.
    :param processor: The admin who suspended the user.
    :param during: The interval in which the user is
        suspended.  If None the user will be suspendeded from now on
        without an upper bound.
    :param violation: If the user should be added to the violation group

    :return: The suspended user.
    """
    if during is None:
        during = starting_from(session.utcnow())

    if violation:
        make_member_of(user, config.violation_group, processor, during)
    else:
        make_member_of(user, config.blocked_group, processor, during)

    message = deferred_gettext("Suspended during {during}. Reason: {reason}.")
    log_user_event(message=message.format(during=during, reason=reason)
                   .to_json(), author=processor, user=user)
    return user


@with_transaction
def unblock(user: User, processor: User, when: DateTimeTz | None = None) -> User:
    """Unblocks a user.

    This removes his membership of the violation, blocken and payment_in_default
    group.

    Note that for unblocking, no further asynchronous action has to be
    triggered, as opposed to e.g. membership termination.

    :param user: The user to be unblocked.
    :param processor: The admin who unblocked the user.
    :param when: The time of membership termination.  Note
        that in comparison to :py:func:`suspend`, you don't provide an
        _interval_, but a point in time, defaulting to the current
        time.  Will be converted to ``starting_from(when)``.

    :return: The unblocked user.
    """
    if when is None:
        when = session.utcnow()

    during = starting_from(when)
    for group in get_blocked_groups():
        if user.member_of(group, when=during):
            remove_member_of(user=user, group=group, processor=processor, during=during)

    return user


@with_transaction
def move_out(
    user: User,
    comment: str,
    processor: User,
    when: DateTimeTz,
    end_membership: bool = True,
) -> User | UserTask:
    """Move out a user and may terminate relevant memberships.

    The user's room is set to ``None`` and all hosts are deleted.
    Memberships in :py:obj:`config.member_group` and
    :py:obj:`config.member_group` are terminated.  A log message is
    created including the number of deleted hosts.

    :param user: The user to move out.
    :param comment: An optional comment
    :param processor: The admin who is going to move out the user.
    :param when: The time the user is going to move out.
    :param end_membership: Ends membership if true

    :return: The user that moved out.
    """
    if when > session.utcnow():
        task_params = UserMoveOutParams(comment=comment, end_membership=end_membership)
        return schedule_user_task(task_type=TaskType.USER_MOVE_OUT,
                                  due=when,
                                  user=user,
                                  parameters=task_params,
                                  processor=processor)

    if end_membership:
        for group in {config.member_group,
                      config.external_group,
                      config.network_access_group}:
            if user.member_of(group):
                remove_member_of(user, group, processor, starting_from(when))

    deleted_interfaces = list()
    num_hosts = 0
    for num_hosts, h in enumerate(user.hosts, 1):  # noqa: B007
        if not h.switch and (h.room == user.room or end_membership):
            for interface in h.interfaces:
                deleted_interfaces.append(interface.mac)

            session.session.delete(h)

    message = None

    if user.room is not None:
        message = "Moved out of {room}: Deleted interfaces {interfaces} of {num_hosts} hosts."\
            .format(room=user.room.short_name,
                    num_hosts=num_hosts,
                    interfaces=', '.join(deleted_interfaces))
        user.room = None
    elif num_hosts:
        message = "Deleted interfaces {interfaces} of {num_hosts} hosts." \
            .format(num_hosts=num_hosts, interfaces=', '.join(deleted_interfaces))

    if message is not None:
        if comment:
            message += f"\nComment: {comment}"

        log_user_event(
            message=deferred_gettext(message).to_json(),
            author=processor,
            user=user
        )

    return user


admin_properties = property.property_categories["Nutzerverwaltung"].keys()


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
        admin=any(prop in user.current_properties for prop in admin_properties),
    )


def membership_ending_task(user: User) -> UserTask:
    """
    :return: Next task that will end the membership of the user
    """

    return t.cast(
        UserTask,
        UserTask.q.filter_by(
            user_id=user.id, status=TaskStatus.OPEN, type=TaskType.USER_MOVE_OUT
        )
        # Casting jsonb -> bool directly is only supported since PG v11
        .filter(
            UserTask.parameters_json["end_membership"].cast(String).cast(Boolean)
        )
        .order_by(UserTask.due.asc())
        .first(),
    )


def membership_end_date(user: User) -> date | None:
    """
    :return: The due date of the task that will end the membership; None if not
             existent
    """

    ending_task = membership_ending_task(user)

    end_date = None if ending_task is None else ending_task.due.date()

    return end_date


def membership_beginning_task(user: User) -> UserTask:
    """
    :return: Next task that will end the membership of the user
    """

    return t.cast(
        UserTask,
        UserTask.q.filter_by(
            user_id=user.id, status=TaskStatus.OPEN, type=TaskType.USER_MOVE_IN
        )
        .filter(UserTask.parameters_json["begin_membership"].cast(Boolean))
        .order_by(UserTask.due.asc())
        .first(),
    )


def membership_begin_date(user: User) -> date | None:
    """
    :return: The due date of the task that will begin a membership; None if not
             existent
    """

    begin_task = membership_beginning_task(user)

    end_date = None if begin_task is None else begin_task.due.date()

    return end_date


@with_transaction
def send_password_reset_mail(user: User) -> bool:
    user.password_reset_token = generate_random_str(64)

    if not password_reset_url:
        raise ValueError("No url specified in PASSWORD_RESET_URL")

    try:
        user_send_mail(user, UserResetPasswordTemplate(
                       password_reset_url=password_reset_url.format(user.password_reset_token)),
                       use_internal=False)
    except ValueError:
        user.password_reset_token = None
        return False

    return True
