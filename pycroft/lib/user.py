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
import re
import typing
from datetime import datetime, timedelta, date
from difflib import SequenceMatcher
from typing import Iterable

from sqlalchemy import func, select, Boolean, String
from sqlalchemy.engine import Row

from pycroft import config, property
from pycroft.helpers import user as user_helper, AttrDict, utc
from pycroft.helpers.errorcode import Type1Code, Type2Code
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import closed, closedopen
from pycroft.helpers.printing import generate_user_sheet as generate_pdf
from pycroft.helpers.user import generate_random_str
from pycroft.lib.address import get_or_create_address
from pycroft.lib.exc import PycroftLibException
from pycroft.lib.facilities import get_room
from pycroft.lib.finance import user_has_paid
from pycroft.lib.logging import log_user_event, log_event
from pycroft.lib.mail import MailTemplate, Mail, UserConfirmEmailTemplate, \
    UserCreatedTemplate, \
    UserMovedInTemplate, MemberRequestPendingTemplate, \
    MemberRequestDeniedTemplate, \
    MemberRequestMergedTemplate, UserResetPasswordTemplate
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.lib.net import get_free_ip, MacExistsException, \
    get_subnets_for_room
from pycroft.lib.swdd import get_relevant_tenancies
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
from pycroft.model.user import User, UnixAccount, PreMember, BaseUser, \
    RoomHistoryEntry, \
    PropertyGroup
from pycroft.model.webstorage import WebStorage
from pycroft.task import send_mails_async

mail_confirm_url = os.getenv('MAIL_CONFIRM_URL')
password_reset_url = os.getenv('PASSWORD_RESET_URL')


def encode_type1_user_id(user_id):
    """Append a type-1 error detection code to the user_id."""
    return f"{user_id:04d}-{Type1Code.calculate(user_id):d}"


type1_user_id_pattern = re.compile(r"^(\d{4,})-(\d)$")


def decode_type1_user_id(string):
    """
    If a given string is a type1 user id return a (user_id, code) tuple else
    return None.

    :param unicode string: Type1 encoded user ID
    :returns: (number, code) pair or None
    :rtype: (Integral, Integral) | None
    """
    match = type1_user_id_pattern.match(string)
    return match.groups() if match else None


def encode_type2_user_id(user_id):
    """Append a type-2 error detection code to the user_id."""
    return f"{user_id:04d}-{Type2Code.calculate(user_id):02d}"


type2_user_id_pattern = re.compile(r"^(\d{4,})-(\d{2})$")


def decode_type2_user_id(string):
    """
    If a given string is a type2 user id return a (user_id, code) tuple else
    return None.

    :param unicode string: Type2 encoded user ID
    :returns: (number, code) pair or None
    :rtype: (Integral, Integral) | None
    """
    match = type2_user_id_pattern.match(string)
    return match.groups() if match else None


def check_user_id(string):
    """
    Check if the given string is a valid user id (type1 or type2).

    :param string: Type1 or Type2 encoded user ID
    :returns: True if user id was valid, otherwise False
    :rtype: Boolean
    """
    if not string:
        return False

    idsplit = string.split("-")
    if len(idsplit) != 2:
        return False
    uid = idsplit[0]
    code = idsplit[1]

    if len(code) == 2:
        # Type2 code
        verify = encode_type2_user_id(int(uid))
    else:
        # Type1 code
        verify = encode_type1_user_id(int(uid))

    if string == verify:
        return True
    else:
        return False


class HostAliasExists(ValueError):
    pass


def setup_ipv4_networking(host):
    """Add suitable ips for every interface of a host"""
    subnets = get_subnets_for_room(host.room)

    for interface in host.interfaces:
        ip_address, subnet = get_free_ip(subnets)
        new_ip = IP(interface=interface, address=ip_address,
                    subnet=subnet)
        session.session.add(new_ip)


def store_user_sheet(new_user, wifi, user=None, timeout=15, plain_user_password=None,
                     generation_purpose='', plain_wifi_password=''):
    """Generate a user sheet and store it in the WebStorage.

    Returns the generated :class:`WebStorage <pycroft.model.WebStorage>` object holding the pdf.

    :param bool new_user: generate page with user details
    :param bool wifi: generate page with wifi credantials
    :param int timeout: The lifetime in minutes
    :param User user: A pycroft user. Necessary in every case
    :param str plain_user_password: Only necessary if ``new_user is True``
    :param str plain_wifi_password: The password for wifi.  Only necessary if ``wifi is True``
    :param str generation_purpose: Optional
    """

    pdf_data = generate_user_sheet(
        new_user, wifi, user,
        plain_user_password=plain_user_password,
        generation_purpose=generation_purpose,
        plain_wifi_password=plain_wifi_password,
    )

    pdf_storage = WebStorage(data=pdf_data,
                             expiry=session.utcnow() + timedelta(minutes=timeout))
    session.session.add(pdf_storage)

    return pdf_storage


def get_user_sheet(sheet_id):
    """Fetch the storage object given an id.

    If not existent, return None.
    """
    WebStorage.auto_expire()

    if sheet_id is None:
        return None
    if (storage := WebStorage.get(sheet_id)) is None:
        return None

    return storage.data


@with_transaction
def reset_password(user, processor):
    if not can_target(user, processor):
        raise PermissionError("cannot reset password of a user with a"
                              " greater or equal permission level.")

    plain_password = user_helper.generate_password(12)
    user.password = plain_password

    message = deferred_gettext("Password was reset")
    log_user_event(author=processor,
                   user=user,
                   message=message.to_json())

    return plain_password

def can_target(user, processor):
    if user != processor:
        return user.permission_level < processor.permission_level
    else:
        return True


@with_transaction
def reset_wifi_password(user: User, processor: User) -> str:
    plain_password = generate_wifi_password()
    user.wifi_password = plain_password

    message = deferred_gettext("WIFI-Password was reset")
    log_user_event(author=processor,
                   user=user,
                   message=message.to_json())

    return plain_password


def maybe_setup_wifi(user: User, processor: User) -> str | None:
    """If wifi is available, sets a wifi password."""
    if user.room and user.room.building.wifi_available:
        return reset_wifi_password(user, processor)
    return None


@with_transaction
def change_password(user, password):
    # TODO: verify password complexity
    user.password = password

    message = deferred_gettext("Password was changed")
    log_user_event(author=user,
                   user=user,
                   message=message.to_json())


def generate_wifi_password() -> str:
    return user_helper.generate_password(12)


def create_user(
    name: str, login: str, email: str, birthdate: date,
    groups: list[PropertyGroup], processor: User | None, address: Address,
    passwd_hash: str = None,
    send_confirm_mail: bool = False
):
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
    """

    now = session.utcnow()
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


@with_transaction
def move_in(
    user: User,
    building_id: int, level: int, room_number: str,
    mac: str | None,
    processor: User | None = None,
    birthdate: date = None,
    host_annex: bool = False,
    begin_membership: bool = True,
    when: datetime | None = None
):
    """Move in a user in a given room and do some initialization.

    The user is given a new Host with an interface of the given mac, a
    UnixAccount, a finance Account, and is made member of important
    groups.  Networking is set up.

    :param User user: The user to move in
    :param building_id:
    :param level:
    :param room_number:
    :param mac: The mac address of the users pc.
    :param processor:
    :param birthdate: Date of birth`
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
                remove_member_of(user, group, processor, closedopen(session.utcnow(), None))

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


def migrate_user_host(host, new_room, processor):
    """
    Migrate a UserHost to a new room and if necessary to a new subnet.
    If the host changes subnet, it will get a new IP address.

    :param Host host: Host to be migrated
    :param Room new_room: new room of the host
    :param User processor: User processing the migration
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
@with_transaction
def move(user, building_id, level, room_number, processor, comment=None, when=None):
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
    :rtype: User
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


@with_transaction
def edit_name(user, name, processor):
    """Changes the name of the user and creates a log entry.

    :param user: The user object.
    :param name: The new full name.
    :return: The changed user object.
    """

    if not name:
        raise ValueError()

    if name == user.name:
        # name wasn't changed, do nothing
        return user

    old_name = user.name
    user.name = name
    message = deferred_gettext("Changed name from {} to {}.")
    log_user_event(author=processor, user=user,
                   message=message.format(old_name, name).to_json())
    return user


@with_transaction
def edit_email(user: User, email: str | None, email_forwarded: bool, processor: User,
               is_confirmed: bool = False):
    """
    Changes the email address of a user and creates a log entry.

    :param user: User object to change
    :param email: New email address (empty interpreted as ``None``)
    :param email_forwarded: Boolean if emails should be forwarded
    :param processor: User object of the processor, which issues the change
    :param is_confirmed: If the email address is already confirmed
    :return:Changed user object
    """

    if not can_target(user, processor):
        raise PermissionError("cannot change email of a user with a"
                              " greater or equal permission level.")

    if not email:
        email = None
    else:
        email = email.lower()

    if email_forwarded != user.email_forwarded:
        user.email_forwarded = email_forwarded

        log_user_event(author=processor, user=user,
                       message=deferred_gettext("Set e-mail forwarding to {}.")
                               .format(email_forwarded).to_json())

    if is_confirmed:
        user.email_confirmed = True
        user.email_confirmation_key = None

    if email == user.email:
        # email wasn't changed, do nothing
        return user

    old_email = user.email
    user.email = email

    if email is not None:
        if not is_confirmed:
            send_confirmation_email(user)
    else:
        user.email_confirmed = False
        user.email_confirmation_key = None

    message = deferred_gettext("Changed e-mail from {} to {}.")
    log_user_event(author=processor, user=user,
                   message=message.format(old_email, email).to_json())
    return user


@with_transaction
def edit_birthdate(user, birthdate, processor):
    """
    Changes the birthdate of a user and creates a log entry.

    :param user: User object to change
    :param birthdate: New birthdate
    :param processor:User object of the processor, which issues the change
    :return:Changed user object
    """

    if not birthdate:
        birthdate = None

    if birthdate == user.birthdate:
        # birthdate wasn't changed, do nothing
        return user

    old_bd = user.birthdate
    user.birthdate = birthdate
    message = deferred_gettext("Changed birthdate from {} to {}.")
    log_user_event(author=processor, user=user,
                   message=message.format(old_bd, birthdate).to_json())
    return user


@with_transaction
def edit_person_id(user: User, person_id: int, processor: User):
    """
    Changes the swdd_person_id of the user and creates a log entry.

    :param user: The user object.
    :param person_id: The new person_id.
    :return: The changed user object.
    """

    if person_id == user.swdd_person_id:
        # name wasn't changed, do nothing
        return user

    old_person_id = user.swdd_person_id
    user.swdd_person_id = person_id
    message = deferred_gettext("Changed tenant number from {} to {}.")
    log_user_event(author=processor, user=user,
                   message=message.format(str(old_person_id), str(person_id)).to_json())

    return user


@with_transaction
def edit_address(
    user: User,
    processor: User,
    street: str,
    number: str,
    addition: str | None,
    zip_code: str,
    city: str | None,
    state: str | None,
    country: str | None,
):
    """Changes the address of a user and appends a log entry.

    Should do nothing if the user already has an address.
    """
    address = get_or_create_address(street, number, addition, zip_code, city, state, country)
    user.address = address
    log_user_event(deferred_gettext("Changed address to {address}").format(address=str(address)).to_json(),
                   processor, user)


def traffic_history(user_id, start, end) -> list[TrafficHistoryEntry]:
    result: list[Row] = session.session.execute(
        select('*').select_from(
            func.traffic_history(user_id, start, end))).fetchall()
    return [TrafficHistoryEntry(**dict(row)) for row in result]


def has_balance_of_at_least(user, amount):
    """Check whether the given user's balance is at least the given
    amount.

    If a user does not have an account, we treat his balance as if it
    were exactly zero.

    :param User user: The user we are interested in.
    :param Integral amount: The amount we want to check for.
    :return: True if and only if the user's balance is at least the given
        amount (and False otherwise).
    """
    balance = user.account.balance if user.account else 0
    return balance >= amount


def has_positive_balance(user):
    """Check whether the given user's balance is (weakly) positive.

    :param user: The user we are interested in.
    :return: True if and only if the user's balance is at least zero.
    """
    return has_balance_of_at_least(user, 0)


def get_blocked_groups():
    return [config.violation_group, config.payment_in_default_group,
                      config.blocked_group]


@with_transaction
def block(user, reason, processor, during=None, violation=True):
    """Suspend a user during a given interval.

    The user is added to violation_group or blocked_group in a given
    interval.  A reason needs to be provided.

    :param User user: The user to be suspended.
    :param unicode reason: The reason for suspending.
    :param User processor: The admin who suspended the user.
    :param Interval|None during: The interval in which the user is
        suspended.  If None the user will be suspendeded from now on
        without an upper bound.
    :param Boolean violation: If the user should be added to the violation group

    :return: The suspended user.
    """
    if during is None:
        during = closedopen(session.utcnow(), None)

    if violation:
        make_member_of(user, config.violation_group, processor, during)
    else:
        make_member_of(user, config.blocked_group, processor, during)

    message = deferred_gettext("Suspended during {during}. Reason: {reason}.")
    log_user_event(message=message.format(during=during, reason=reason)
                   .to_json(), author=processor, user=user)
    return user


@with_transaction
def unblock(user, processor, when=None):
    """Unblocks a user.

    This removes his membership of the violation, blocken and payment_in_default
    group.

    Note that for unblocking, no further asynchronous action has to be
    triggered, as opposed to e.g. membership termination.

    :param User user: The user to be unblocked.
    :param User processor: The admin who unblocked the user.
    :param datetime when: The time of membership termination.  Note
        that in comparison to :py:func:`suspend`, you don't provide an
        _interval_, but a point in time, defaulting to the current
        time.  Will be converted to ``closedopen(when, None)``.

    :return: The unblocked user.
    """
    if when is None:
        when = session.utcnow()

    for group in get_blocked_groups():
        if user.member_of(group):
            remove_member_of(user=user, group=group,
                             processor=processor, during=closedopen(when, None))

    return user


@with_transaction
def move_out(user, comment, processor, when, end_membership=True):
    """Move out a user and may terminate relevant memberships.

    The user's room is set to ``None`` and all hosts are deleted.
    Memberships in :py:obj:`config.member_group` and
    :py:obj:`config.member_group` are terminated.  A log message is
    created including the number of deleted hosts.

    :param User user: The user to move out.
    :param unicode|None comment: An optional comment
    :param User processor: The admin who is going to move out the
        user.
    :param datetime when: The time the user is going to move out.
    :param bool end_membership: Ends membership if true

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
                remove_member_of(user, group, processor, closedopen(when, None))

    deleted_interfaces = list()
    num_hosts = 0
    for num_hosts, h in enumerate(user.hosts, 1):
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
        had_custom_address = user.has_custom_address
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


def status(user):
    """
    :param user: User whose status we want to look at
    :return: dict of boolean status codes
    """

    current_groups = user.active_property_groups()
    has_interface = any(h.interfaces for h in user.hosts)
    return AttrDict({
        'member': config.member_group in current_groups,
        'traffic_exceeded': config.traffic_limit_exceeded_group in current_groups,
        'network_access': user.has_property('network_access') and has_interface,
        'wifi_access': user.has_wifi_access and user.has_property('network_access'),
        'account_balanced': user_has_paid(user),
        'violation': user.has_property('violation'),
        'ldap': user.has_property('ldap'),
        'admin': any(user.has_property(prop) for prop in admin_properties),
    })


def generate_user_sheet(new_user, wifi, user=None, plain_user_password=None, generation_purpose='',
                        plain_wifi_password=''):
    """Create a new datasheet for the given user.
    This usersheet can hold information about a user or about the wifi credentials of a user.

    This is a wrapper for
    :py:func:`pycroft.helpers.printing.generate_user_sheet` equipping
    it with the correct user id.

    This function cannot be exported to a `wrappers` module because it
    depends on `encode_type2_user_id` and is required by
    `(store|get)_user_sheet`, both in this module.

    :param bool new_user: Generate a page for a new created user
    :param bool wifi: Generate a page with the wifi credantials

    Necessary in every case:
    :param User user: A pycroft user

    Only necessary if new_user=True:
    :param str plain_user_password: The password

    Only necessary if wifi=True:
    :param generation_purpose: Optional purpose why this usersheet was printed
    """
    return generate_pdf(new_user, wifi, user, user_id=encode_type2_user_id(user.id),
                        plain_user_password=plain_user_password,
                        generation_purpose=generation_purpose,
                        plain_wifi_password=plain_wifi_password)


def membership_ending_task(user):
    """
    :return: Next task that will end the membership of the user
    """

    task = (UserTask.q
            .filter_by(user_id=user.id,
                       status=TaskStatus.OPEN,
                       type=TaskType.USER_MOVE_OUT)
            # Casting jsonb -> bool directly is only supported since PG v11
            .filter(UserTask.parameters_json['end_membership'].cast(String).cast(Boolean) == True)
            .order_by(UserTask.due.asc())).first()

    return task


def membership_end_date(user):
    """
    :return: The due date of the task that will end the membership; None if not
             existent
    """

    ending_task = membership_ending_task(user)

    end_date = None if ending_task is None else ending_task.due.date()

    return end_date


def membership_beginning_task(user):
    """
    :return: Next task that will end the membership of the user
    """

    task = (UserTask.q
            .filter_by(user_id=user.id,
                       status=TaskStatus.OPEN,
                       type=TaskType.USER_MOVE_IN)
            .filter(UserTask.parameters_json['begin_membership'].cast(Boolean) == True)
            .order_by(UserTask.due.asc())).first()

    return task


def membership_begin_date(user):
    """
    :return: The due date of the task that will begin a membership; None if not
             existent
    """

    begin_task = membership_beginning_task(user)

    end_date = None if begin_task is None else begin_task.due.date()

    return end_date


def format_user_mail(user: User, text: str):
    return text.format(
        name=user.name,
        login=user.login,
        id=encode_type2_user_id(user.id),
        email=user.email if user.email else '-',
        email_internal=user.email_internal,
        room_short=user.room.short_name
        if user.room_id is not None else '-',
        swdd_person_id=user.swdd_person_id
        if user.swdd_person_id else '-',
    )


def user_send_mails(users: list[BaseUser], template: MailTemplate | None = None,
                    soft_fail: bool = False,
                    use_internal: bool = True,
                    body_plain: str = None,
                    subject: str = None,
                    **kwargs):
    """
    Send a mail to a list of users

    :param users: Users who should receive the mail
    :param template: The template that should be used. Can be None if body_plain is supplied.
    :param soft_fail: Do not raise an exception if a user does not have an email and use_internal
        is set to True
    :param use_internal: If internal mail addresses can be used (@agdsn.me)
        (Set to False to only send to external mail addresses)
    :param body_plain: Alternative plain body if not template supplied
    :param subject:  Alternative subject if no template supplied
    :param kwargs: kwargs that will be used during rendering the template
    :return:
    """

    mails = []

    for user in users:
        if isinstance(user, User) and all((use_internal,
                                           not (user.email_forwarded and user.email),
                                           user.has_property('mail'))):
            # Use internal email
            email = user.email_internal
        elif user.email:
            # Use external email
            email = user.email
        else:
            if soft_fail:
                return
            else:
                raise ValueError("No contact email address available.")

        if template is not None:
            # Template given, render...
            plaintext, html = template.render(user=user,
                                              user_id=encode_type2_user_id(user.id),
                                              **kwargs)
            subject = template.subject
        else:
            # No template given, use formatted body_mail instead.
            if not isinstance(user, User):
                raise ValueError("Plaintext email not supported for other User types.")

            html = None
            plaintext = format_user_mail(user, body_plain)

        if plaintext is None or subject is None:
            raise ValueError("No plain body supplied.")

        mail = Mail(to_name=user.name,
                    to_address=email,
                    subject=subject,
                    body_plain=plaintext,
                    body_html=html)
        mails.append(mail)

    send_mails_async.delay(mails)


def user_send_mail(user: BaseUser, template: MailTemplate, soft_fail: bool = False,
                   use_internal: bool = True, **kwargs):
    user_send_mails([user], template, soft_fail, use_internal, **kwargs)


def group_send_mail(group: PropertyGroup, subject: str, body_plain: str):
    active_memberships = User.active_memberships()

    users = User.q.join(active_memberships)\
        .filter(active_memberships.c.group_id == group.id).distinct().all()

    user_send_mails(users, soft_fail=True, body_plain=body_plain, subject=subject)


def send_member_request_merged_email(user: PreMember, merged_to: User, password_merged: bool):
    user_send_mail(user, MemberRequestMergedTemplate(merged_to=merged_to,
                                                     merged_to_user_id=encode_type2_user_id(
                                                         merged_to.id),
                                                     password_merged=password_merged))


@with_transaction
def send_confirmation_email(user: BaseUser):
    user.email_confirmed = False
    user.email_confirmation_key = generate_random_str(64)

    if not mail_confirm_url:
        raise ValueError("No url specified in MAIL_CONFIRM_URL")

    user_send_mail(user, UserConfirmEmailTemplate(
        email_confirm_url=mail_confirm_url.format(user.email_confirmation_key)))


class LoginTakenException(PycroftLibException):
    def __init__(self):
        super().__init__("Login already taken")


class EmailTakenException(PycroftLibException):
    def __init__(self):
        super().__init__("E-Mail address already in use")


class UserExistsInRoomException(PycroftLibException):
    def __init__(self):
        super().__init__("A user with a similar name already lives in this room")


class UserExistsException(PycroftLibException):
    def __init__(self):
        super().__init__("This user already exists")


class NoTenancyForRoomException(PycroftLibException):
    def __init__(self):
        super().__init__("This user has no tenancy in that room")


class MoveInDateInvalidException(PycroftLibException):
    def __init__(self):
        super().__init__("The move-in date is invalid (in the past or more than 6 months in the future)")


def get_similar_users_in_room(name: str, room: Room, ratio: float = 0.75):
    """
    Get users with a 75% name match already exists in the room
    """

    if room is None:
        return []

    users = User.q.filter_by(room=room).all()
    users_match = []

    for user in users:
        ratio_is = SequenceMatcher(None, name, user.name).ratio()

        if ratio_is > ratio:
            users_match.append(user)

    return users_match


def check_similar_user_in_room(name: str, room: Room):
    """
    Raise an error if an user with a 75% name match already exists in the room
    """

    if len(get_similar_users_in_room(name, room)) > 0:
        raise UserExistsInRoomException


def get_user_by_swdd_person_id(swdd_person_id: int | None) -> User | None:
    if swdd_person_id is None:
        return None

    return typing.cast(
        User | None,
        User.q.filter_by(swdd_person_id=swdd_person_id).first()
    )


def check_new_user_data(login: str, email: str, name: str, swdd_person_id: int | None,
                        room: Room | None, move_in_date: date | None,
                        ignore_similar_name: bool = False, allow_existing: bool = False):
    user_swdd_person_id = get_user_by_swdd_person_id(swdd_person_id)

    if user_swdd_person_id and not allow_existing:
        raise UserExistsException

    user_login = User.q.filter_by(login=login).first()

    if user_login is not None and not allow_existing:
        raise LoginTakenException

    user_email = User.q.filter_by(email=email).first()

    if user_email is not None and not allow_existing:
        raise EmailTakenException

    if room is not None and not ignore_similar_name:
        check_similar_user_in_room(name, room)

    if move_in_date is not None:
        if move_in_date > (session.utcnow() + timedelta(days=180)).date() or move_in_date < session.utcnow().date():
            raise MoveInDateInvalidException


@with_transaction
def create_member_request(name: str, email: str, password: str, login: str,
                          birthdate: date, swdd_person_id: int | None, room: Room | None,
                          move_in_date: date | None, previous_dorm: str | None,):
    check_new_user_data(login, email, name, swdd_person_id, room, move_in_date,
                        allow_existing=previous_dorm is not None)

    if swdd_person_id is not None and room is not None:
        tenancies = get_relevant_tenancies(swdd_person_id)

        rooms = [tenancy.room for tenancy in tenancies]

        if room not in rooms:
            raise NoTenancyForRoomException

    mr = PreMember(name=name, email=email, swdd_person_id=swdd_person_id,
                   password=password,  room=room, login=login, move_in_date=move_in_date,
                   birthdate=birthdate, registered_at=session.utcnow(),
                   previous_dorm=previous_dorm)

    session.session.add(mr)
    session.session.flush()

    # Send confirmation mail
    send_confirmation_email(mr)

    return mr


@with_transaction
def finish_member_request(prm: PreMember, processor: User | None,
                          ignore_similar_name: bool = False):
    if prm.room is None:
        raise ValueError("Room is None")

    if prm.move_in_date is not None and prm.move_in_date < session.utcnow().date():
        prm.move_in_date = session.utcnow().date()

    check_new_user_data(prm.login, prm.email, prm.name, prm.swdd_person_id, prm.room,
                        prm.move_in_date, ignore_similar_name)

    user, _ = create_user(prm.name, prm.login, prm.email, prm.birthdate, groups=[],
                          processor=processor, address=prm.room.address, passwd_hash=prm.passwd_hash)

    processor = processor if processor is not None else user

    user.swdd_person_id = prm.swdd_person_id
    user.email_confirmed = prm.email_confirmed

    move_in_datetime = utc.with_min_time(prm.move_in_date)

    move_in(user, prm.room.building_id, prm.room.level, prm.room.number, None,
            processor if processor is not None else user, when=move_in_datetime)

    message = deferred_gettext("Created from registration {}.").format(str(prm.id)).to_json()
    log_user_event(message, processor, user)

    if move_in_datetime > session.utcnow():
        make_member_of(user, config.pre_member_group, processor,
                       closed(session.utcnow(), None))

    session.session.delete(prm)

    return user


@with_transaction
def confirm_mail_address(key):
    if not key:
        raise ValueError("No key given")

    mr = PreMember.q.filter_by(email_confirmation_key=key).one_or_none()
    user = User.q.filter_by(email_confirmation_key=key).one_or_none()

    if mr is None and user is None:
        raise ValueError("Unknown confirmation key")
    elif user is None:
        if mr.email_confirmed:
            raise ValueError("E-Mail already confirmed")

        mr.email_confirmed = True
        mr.email_confirmation_key = None

        if mr.swdd_person_id is not None and mr.room is not None and mr.previous_dorm is None \
           and mr.is_adult:
            finish_member_request(mr, None)
            reg_result = 'account_created'
        else:
            user_send_mail(mr, MemberRequestPendingTemplate(is_adult=mr.is_adult))
            reg_result = 'request_pending'

        return 'pre_member', reg_result
    elif mr is None:
        user.email_confirmed = True
        user.email_confirmation_key = None

        return 'user', None


def get_member_requests():
    prms = PreMember.q.order_by(PreMember.email_confirmed.desc())\
        .order_by(PreMember.registered_at.asc()).all()

    return prms


def get_name_from_first_last(first_name: str, last_name: str):
    return f"{first_name} {last_name}" if last_name else first_name


@with_transaction
def delete_member_request(prm: PreMember, reason: str | None, processor: User,
                          inform_user: bool = True):

    if reason is None:
        reason = "Keine Begründung angegeben."

    log_event(deferred_gettext("Deleted member request {}. Reason: {}").format(prm.id, reason).to_json(),
              processor)

    if inform_user:
        user_send_mail(prm, MemberRequestDeniedTemplate(reason=reason), soft_fail=True)

    session.session.delete(prm)


@with_transaction
def merge_member_request(user: User, prm: PreMember, merge_name: bool, merge_email: bool,
                         merge_person_id: bool, merge_room: bool, merge_password: bool,
                         merge_birthdate: bool, processor: User):
    if prm.move_in_date is not None and prm.move_in_date < session.utcnow().date():
        prm.move_in_date = session.utcnow().date()

    if merge_name:
        user = edit_name(user, prm.name, processor)

    if merge_email:
        user = edit_email(user, prm.email, user.email_forwarded, processor,
                          is_confirmed=prm.email_confirmed)

    if merge_person_id:
        user = edit_person_id(user, prm.swdd_person_id, processor)

    move_in_datetime = utc.with_min_time(prm.move_in_date)

    if merge_room:
        if prm.room:
            if user.room:
                move(user, prm.room.building_id, prm.room.level, prm.room.number,
                     processor=processor, when=move_in_datetime)

                if not user.member_of(config.member_group):
                    make_member_of(user, config.member_group, processor,
                                   closed(move_in_datetime, None))

                    if move_in_datetime > session.utcnow():
                        make_member_of(user, config.pre_member_group, processor,
                                       closed(session.utcnow(), move_in_datetime))
            else:
                move_in(user, prm.room.building_id, prm.room.level, prm.room.number,
                        mac=None, processor=processor, when=move_in_datetime)

                if move_in_datetime > session.utcnow():
                    make_member_of(user, config.pre_member_group, processor,
                                   closed(session.utcnow(), None))

    if merge_birthdate:
        user = edit_birthdate(user, prm.birthdate, processor)

    log_msg = "Merged information from registration {}."

    if merge_password:
        user.passwd_hash = prm.passwd_hash

        log_msg += " Password overridden."
    else:
        log_msg += " Kept old password."

    log_user_event(deferred_gettext(log_msg).format(encode_type2_user_id(prm.id)).to_json(),
                   processor, user)

    session.session.delete(prm)


def get_possible_existing_users_for_pre_member(prm: PreMember):
    user_swdd_person_id = get_user_by_swdd_person_id(prm.swdd_person_id)
    user_login = User.q.filter_by(login=prm.login).first()
    user_email = User.q.filter(func.lower(User.email) == prm.email.lower()).first()

    users_name = User.q.filter_by(name=prm.name).all()
    users_similar = get_similar_users_in_room(prm.name, prm.room, 0.5)

    users = {user for user in [user_swdd_person_id, user_login, user_email]
             + users_name + users_similar if user is not None}

    return users


def get_user_by_id_or_login(ident: str, email: str):
    re_uid1 = r"^\d{4,6}-\d{1}$"
    re_uid2 = r"^\d{4,6}-\d{2}$"

    user = User.q.filter(func.lower(User.email) == email.lower())

    if re.match(re_uid1, ident):
        if check_user_id(ident):
            user_id = decode_type1_user_id(ident)

            user = user.filter_by(id=user_id[0])
        else:
            return None
    elif re.match(re_uid2, ident):
        if check_user_id(ident):
            user_id = decode_type2_user_id(ident)

            user = user.filter_by(id=user_id[0])
        else:
            return None
    elif re.match(BaseUser.login_regex, ident):
        user = user.filter_by(login=ident)

    user = user.one_or_none()

    return user


@with_transaction
def send_password_reset_mail(user: User):
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


@with_transaction
def change_password_from_token(token, password):
    if token is None:
        return False

    user = User.q.filter_by(password_reset_token=token).one_or_none()

    if user:
        change_password(user, password)
        user.password_reset_token = None
        user.email_confirmed = True

        return True
    else:
        return False


def find_similar_users(name: str, room: Room, ratio: float) -> Iterable[User]:
    """Given a potential user's name and a room, find users of similar name living in that room.

    :param name: The potential user's name
    :param room: the room whose inhabitants to search
    :param ratio: the threshold which determines which matches are included in this list.
      For that, the `difflib.SequenceMatcher.ratio` must be greater than the given value.
    """
    relevant_users_q = (session.session.query(User)
        .join(RoomHistoryEntry)
        .filter(RoomHistoryEntry.room == room))
    return [u for u in relevant_users_q if are_names_similar(name, u.name, threshold=ratio)]


def are_names_similar(one: str, other: str, threshold: float) -> bool:
    return SequenceMatcher(a=one, b=other).ratio() > threshold
