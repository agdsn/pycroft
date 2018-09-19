# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.user
~~~~~~~~~~~~~~

This module contains.

:copyright: (c) 2012 by AG DSN.
"""

import re

from base64 import b64encode, b64decode

from datetime import datetime, timedelta

from sqlalchemy import and_, or_, func, literal, literal_column, union_all, \
    select

from pycroft import config, property
from pycroft.helpers import user as user_helper, AttrDict
from pycroft.helpers.errorcode import Type1Code, Type2Code
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import closed, closedopen, single
from pycroft.helpers.printing import generate_user_sheet as generate_pdf
from pycroft.lib.finance import user_has_paid
from pycroft.lib.logging import log_user_event
from pycroft.lib.membership import make_member_of, remove_member_of
from pycroft.lib.net import get_free_ip, MacExistsException
from pycroft.lib.traffic import setup_traffic_group, grant_initial_credit, \
    NoTrafficGroup
from pycroft.model import session
from pycroft.model.facilities import Room
from pycroft.model.finance import Account
from pycroft.model.host import Host, IP, Host, Interface, Interface
from pycroft.model.session import with_transaction
from pycroft.model.traffic import TrafficHistoryEntry
from pycroft.model.user import User, UnixAccount
from pycroft.model.webstorage import WebStorage


def encode_type1_user_id(user_id):
    """Append a type-1 error detection code to the user_id."""
    return u"{0:04d}-{1:d}".format(user_id, Type1Code.calculate(user_id))


type1_user_id_pattern = re.compile(r"^(\d{4,})-(\d)$")


def decode_type1_user_id(string):
    """
    If a given string is a type1 user id return a (user_id, code) tuple else
    return None.
    :param unicode string: Type1 encoded user ID
    :returns (number, code) pair or None
    :rtype (Integral, Integral) | None
    """
    match = type1_user_id_pattern.match(string)
    return match.groups() if match else None


def encode_type2_user_id(user_id):
    """Append a type-2 error detection code to the user_id."""
    return u"{0:04d}-{1:02d}".format(user_id, Type2Code.calculate(user_id))


type2_user_id_pattern = re.compile(r"^(\d{4,})-(\d{2})$")


def decode_type2_user_id(string):
    """
    If a given string is a type2 user id return a (user_id, code) tuple else
    return None.
    :param unicode string: Type2 encoded user ID
    :returns (number, code) pair or None
    :rtype (Integral, Integral) | None
    """
    match = type2_user_id_pattern.match(string)
    return match.groups() if match else None


def check_user_id(string):
    """
    Check if the given string is a valid user id (type1 or type2).
    :param string: Type1 or Type2 encoded user ID
    :returns True if user id was valid, otherwise False
    :rtype Boolean
    """
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
    subnets = [s for p in host.room.connected_patch_ports
               for v in p.switch_port.default_vlans
               for s in v.subnets
               if s.address.version == 4]
    for interface in host.interfaces:
        ip_address, subnet = get_free_ip(subnets)
        new_ip = IP(interface=interface, address=ip_address,
                    subnet=subnet)
        session.session.add(new_ip)


def store_user_sheet(new_user, plain_password, timeout=15):
    """Generate a user sheet and store it in the WebStorage.

    Returns the generated `WebStorage` object holding the pdf.

    :param User new_user:
    :param str plain_password:
    :param int timeout: The lifetime in minutes
    """
    pdf_data = b64encode(generate_user_sheet(new_user, plain_password)).decode('ascii')
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

    storage = WebStorage.q.get(sheet_id)

    if storage is None:
        return None

    return b64decode(storage.data)


@with_transaction
def reset_password(user, processor):
    plain_password = user_helper.generate_password(12)
    user.password = plain_password

    message = deferred_gettext(u"Password was reset")
    log_user_event(author=processor,
                   user=user,
                   message=message.to_json())

    return plain_password


@with_transaction
def change_password(user, password):
    # TODO: verify password complexity
    user.password = password

    message = deferred_gettext(u"Password was changed")
    log_user_event(author=user,
                   user=user,
                   message=message.to_json())


def create_user(name, login, email, birthdate, groups, processor):
    """Create a new member

    Create a new user with a generated password, finance- and unix account, and make him member
    of the `config.member_group` and `config.network_access_group`.

    :param str name: The full name of the user (e.g. Max Mustermann)
    :param str login: The unix login for the user
    :param str email: E-Mail address of the user
    :param Date birthdate: Date of birth
    :param PropertyGroup groups: The initial groups of the new user
    :param User processor: The processor
    :return:
    """

    now = session.utcnow()
    plain_password = user_helper.generate_password(12)
    # create a new user
    new_user = User(
        login=login,
        name=name,
        email=email,
        registered_at=now,
        account=Account(name="", type="USER_ASSET"),
        password=plain_password,
        birthdate=birthdate
    )

    account = UnixAccount(home_directory="/home/{}".format(login))
    new_user.unix_account = account

    with session.session.begin(subtransactions=True):
        session.session.add(new_user)
        session.session.add(account)
    new_user.account.name = deferred_gettext(u"User {id}").format(
        id=new_user.id).to_json()

    for group in groups:
        make_member_of(new_user, group, processor, closed(now, None))

    log_user_event(author=processor,
                   message=deferred_gettext(u"User created.").to_json(),
                   user=new_user)

    return new_user, plain_password


@with_transaction
def move_in(user, building, level, room_number, mac, processor, birthdate=None,
            traffic_group_id=None, host_annex=False, begin_membership=True):
    """Create a new user in a given room and do some initialization.

    The user is given a new Host with an interface of the given mac, a
    UnixAccount, a finance Account, and is made member of important
    groups.  Networking is set up.

    :param User user: The user to move in
    :param Building building: See :py:func:`create_member`
    :param int level: See :py:func:`create_member`
    :param str room_number: See :py:func:`create_member`
    :param str mac: The mac address of the users pc.
    :param User processor: See :py:func:`create_member
    :param Date birthdate: Date of birth`
    :param int traffic_group_id: the id of the chosen traffic group to
        be used instead of the building's default one.
    :param bool host_annex: when true: if MAC already in use,
        annex host to new user
    :param bool begin_membership: Starts a membership if true
    :return: The user object.
    """

    room = Room.q.filter_by(number=room_number,
                            level=level, building=building).one()

    user.room = room

    if birthdate:
        user.birthdate = birthdate

    if begin_membership:
        if user.member_of(config.external_group):
            remove_member_of(user, config.external_group, processor,
                             closedopen(session.utcnow(), None))

        for group in {config.member_group, config.network_access_group}:
            if not user.member_of(group):
                make_member_of(user, group, processor, closed(session.utcnow(), None))

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

    setup_traffic_group(user, processor, traffic_group_id)
    try:
        grant_initial_credit(user)
    except NoTrafficGroup as e:
        raise ValueError("User {} could not be assigned a traffic group. "
                         "Please specify one manually."
                         .format(user)) from e

    msg = deferred_gettext(u"Moved in: {dorm} {level}-{room}")

    log_user_event(author=processor,
                   message=msg.format(dorm=building.short_name, level=level, room=room_number).to_json(),
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
    subnets = [subnet for p in new_room.connected_patch_ports
               for vlan in p.switch_port.default_vlans
               for subnet in vlan.subnets]
    if old_room.building_id == new_room.building_id:
        return
    for interface in host.interfaces:
        old_ips = tuple(ip for ip in interface.ips)
        for old_ip in old_ips:
            ip_address, subnet = get_free_ip(subnets)
            new_ip = IP(interface=interface, address=ip_address,
                        subnet=subnet)
            session.session.add(new_ip)

            old_address = old_ip.address
            session.session.delete(old_ip)

            message = deferred_gettext(u"Changed IP from {old_ip} to {new_ip}.").format(
                old_ip=str(old_address), new_ip=str(new_ip))
            log_user_event(author=processor, user=host.owner,
                           message=message.to_json())


#TODO ensure serializability
@with_transaction
def move(user, building, level, room_number, processor, traffic_group_id=None):
    """Moves the user into another room.

    :param user: The user to be moved.
    :param building: The new building.
    :param level: The level of the new room.
    :param room_number: The number of the new room.
    :param processor: The user who is currently logged in.
    :param int traffic_group_id: a custom traffic group to use.

    :return: The user object of the moved user.
    :rtype: User
    """

    old_room = user.room
    new_room = Room.q.filter_by(
        number=room_number,
        level=level,
        building_id=building.id
    ).one()

    assert old_room != new_room,\
        "A User is only allowed to move in a different room!"

    user.room = new_room

    message = deferred_gettext(u"Moved from {} to {}.")
    log_user_event(
        author=processor,
        message=message.format(str(old_room), str(new_room)).to_json(),
        user=user
    )

    setup_traffic_group(user, processor, traffic_group_id, terminate_other=True)

    for user_host in user.hosts:
        migrate_user_host(user_host, new_room, processor)

    return user


@with_transaction
def edit_name(user, name, processor):
    """
    Changes the name of the user and creates a log entry.
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
    message = deferred_gettext(u"Changed name from {} to {}.")
    log_user_event(author=processor, user=user,
                   message=message.format(old_name, name).to_json())
    return user


@with_transaction
def edit_email(user, email, processor):
    """
    Changes the email address of a user and creates a log entry.
    :param user: User object to change
    :param email: New email address, can be None
    :param processor:User object of the processor, which issues the change
    :return:Changed user object
    """

    if not email:
        email = None

    if email == user.email:
        # email wasn't changed, do nothing
        return user

    old_email = user.email
    user.email = email
    message = deferred_gettext(u"Changed e-mail from {} to {}.")
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
    message = deferred_gettext(u"Changed birthdate from {} to {}.")
    log_user_event(author=processor, user=user,
                   message=message.format(old_bd, birthdate).to_json())
    return user


def traffic_history(user_id, start, interval, step):
    result = session.session.execute(
        select(['*']).select_from(
            func.traffic_history(user_id, start, interval, step))).fetchall()
    return [TrafficHistoryEntry(**dict(row.items())) for row in result]


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


@with_transaction
def suspend(user, reason, processor, during=None):
    """Suspend a user during a given interval.

    The user is added to ``config.violation_group`` in a given
    interval.  A reason needs to be provided.

    :param User user: The user to be suspended.
    :param unicode reason: The reason for suspending.
    :param User processor: The admin who suspended the user.
    :param Interval|None during: The interval in which the user is
        suspended.  If None the user will be suspendeded from now on
        without an upper bound.

    :return: The suspended user.
    """
    if during is None:
        during = closedopen(session.utcnow(), None)
    make_member_of(user, config.violation_group, processor, during)
    message = deferred_gettext(u"Suspended during {during}. Reason: {reason}.")
    log_user_event(message=message.format(during=during, reason=reason)
                   .to_json(), author=processor, user=user)
    return user


@with_transaction
def unblock(user, processor, when=None):
    """Unblocks a user.

    This removes his membership of the ``config.violation`` group.

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

    remove_member_of(user=user, group=config.violation_group,
                     processor=processor, during=closedopen(when, None))
    message = deferred_gettext(u"User has been unblocked.")
    log_user_event(message=message.to_json(), author=processor, user=user)
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
        raise NotImplementedError("Moving out in the future is not supported yet.")

    if end_membership:
        for group in ({config.member_group,
                       config.network_access_group,
                       config.external_group,
                       config.cache_group}
                      | set(user.traffic_groups)):
            if user.member_of(group):
                remove_member_of(user, group, processor, closedopen(when, None))

        user.birthdate = None

    num_hosts = 0  # In case the chain is empty
    for num_hosts, h in enumerate(user.hosts, 1):
        session.session.delete(h)

    user.room = None

    if comment:
        message = deferred_gettext(
            u"Moved out: ({} hosts deleted). Comment: {}"
        ).format(num_hosts, comment)
    else:
        message = deferred_gettext(
            u"Moved out: ({} hosts deleted)."
        ).format(num_hosts)

    log_user_event(
        message=message.to_json(),
        author=processor,
        user=user
    )

    return user


admin_properties = property.property_categories[u"Nutzerverwaltung"].keys()


def status(user):
    """
    :param user: User whose status we want to look at
    :return: dict of boolean status codes
    """
    return AttrDict({
        'member': user.member_of(config.member_group),
        'traffic_exceeded': user.current_credit < 0,
        'network_access': user.has_property('network_access'),
        'account_balanced': user_has_paid(user),
        'violation': user.has_property('violation'),
        'ldap': user.has_property('ldap'),
        'admin': any(user.has_property(prop) for prop in admin_properties),
    })


def status_query():
    now = single(session.utcnow())
    return session.session.query(
        User,
        User.member_of(config.member_group, now).label('member'),
        # traffic ignored due to pending traffic rework
        literal_column("false").label('traffic_exceeded'),
        (Account.balance <= 0).label('account_balanced'),

        # a User.properties hybrid attribute would be preferrable
        (User.has_property('network_access', now)).label('network_access'),
        (User.has_property('violation', now)).label('violation'),
        (User.has_property('ldap', now)).label('ldap'),
        or_(*(User.has_property(prop, now) for prop in admin_properties)).label('admin')
    ).join(Account)


def generate_user_sheet(user, plain_password):
    """Create a „new member“ datasheet for the given user

    This is a wrapper for
    :py:func:`pycroft.helpers.printing.generate_user_sheet` equipping
    it with the correct user id.

    This function cannot be exported to a `wrappers` module because it
    depends on `encode_type2_user_id` and is required by
    `(store|get)_user_sheet`, both in this module.

    :param User user: A pycroft user
    :param str plain_password: The password
    """
    return generate_pdf(user, encode_type2_user_id(user.id), plain_password)
