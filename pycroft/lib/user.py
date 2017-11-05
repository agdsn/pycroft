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
from __future__ import print_function
from datetime import datetime, time
from itertools import chain
import re

from sqlalchemy import and_, or_, exists, func, literal, literal_column, union_all, select

from pycroft import config, property
from pycroft.helpers import user, AttrDict
from pycroft.helpers.errorcode import Type1Code, Type2Code
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import (
    Interval, IntervalSet, UnboundedInterval, closed, closedopen, single)
from pycroft.lib.host import generate_hostname
from pycroft.lib.net import get_free_ip, ptr_name
from pycroft.model.traffic import TrafficCredit, TrafficVolume, TrafficBalance
from pycroft.model.facilities import Room
from pycroft.model.finance import Account
from pycroft.model.host import Host, IP, UserHost, UserInterface, Interface
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import User, Membership, TrafficGroup, UnixAccount
from pycroft.lib.logging import log_user_event
from pycroft.lib.finance import get_current_semester, user_has_paid


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


# Move down here to solve cyclic import
from pycroft.lib.finance import RegistrationFee, SemesterFee, post_fees


class HostAliasExists(ValueError):
    pass


def setup_ipv4_networking(host):
    """Add suitable ips for every interface of a host"""
    subnets = [s for p in host.room.switch_patch_ports
               for s in p.switch_interface.subnets
               if s.address.version == 4
               if p.switch_interface is not None]
    for interface in host.user_interfaces:
        ip_address, subnet = get_free_ip(subnets)
        new_ip = IP(interface=interface, address=ip_address,
                    subnet=subnet)
        session.session.add(new_ip)


@with_transaction
def move_in(name, login, email, building, level, room_number, mac,
            processor, moved_from_division, already_paid_semester_fee):
    """
    This function creates a new user, assign him to a room and creates some
    initial groups and transactions.
    :param name: The full name of the user. (Max Mustermann)
    :param login: The unix login for the user.
    :param email: E-Mail address of the user.
    :param building: The building the user moves in.
    :param level: The level the user moves in.
    :param room_number: The room number the user moves in.
    :param mac: The mac address of the users pc.
    :param moved_from_division: User was already member of another division
    :param already_paid_semester_fee: User paid at other division for current semester
    :param host_name: An optional Hostname for the users pc.
    :return: The new user object.
    """

    room = Room.q.filter_by(number=room_number,
        level=level, building=building).one()

    now = session.utcnow()
    plain_password = user.generate_password(12)
    # create a new user
    new_user = User(
        login=login,
        name=name,
        email=email,
        room=room,
        registered_at=now,
        account=Account(name="", type="USER_ASSET"),
        password=plain_password
    )

    account = UnixAccount(home_directory="/home/{}".format(login))
    new_user.unix_account = account

    with session.session.begin(subtransactions=True):
        session.session.add(new_user)
        session.session.add(account)
    new_user.account.name = deferred_gettext(u"User {id}").format(
        id=new_user.id).to_json()

    # create one new host (including interface) for the new user
    new_host = UserHost(owner=new_user, room=room)
    session.session.add(new_host)
    session.session.add(UserInterface(mac=mac, host=new_host))
    setup_ipv4_networking(new_host)

    for group in (config.member_group, config.network_access_group):
        make_member_of(new_user, group, processor, closed(now, None))

    if moved_from_division:
        group = config.moved_from_division_group
        make_member_of(new_user, group, processor, closedopen(now, None))

    if already_paid_semester_fee:
        group = config.already_paid_semester_fee_group
        during = closed(now, datetime.combine(
            get_current_semester().ends_on, time.max))
        make_member_of(new_user, group, processor, during)

    fees = [
        RegistrationFee(config.registration_fee_account),
        SemesterFee(config.semester_fee_account),
    ]
    # Post initial fees
    post_fees([new_user], fees, processor)

    log_user_event(author=processor,
                   message=deferred_gettext(u"Moved in.").to_json(),
                   user=new_user)

    #TODO: print plain password on paper instead
    print(u"new password: " + plain_password)

    return new_user


def migrate_user_host(host, new_room, processor):
    """
    Migrate a UserHost to a new room and if necessary to a new subnet.
    If the host changes subnet, it will get a new IP address.
    :param UserHost host: Host to be migrated
    :param Room new_room: new room of the host
    :param User processor: User processing the migration
    :return:
    """
    old_room = host.room
    host.room = new_room
    subnets = [subnet for p in new_room.switch_patch_ports
               for subnet in p.switch_interface.subnets]
    if old_room.building_id == new_room.building_id:
        return
    for interface in host.user_interfaces:
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
def move(user, building, level, room_number, processor):
    """
    Moves the user into another room.
    :param user: The user to be moved.
    :param building: The new building.
    :param level: The level of the new room.
    :param room_number: The number of the new room.
    :param processor: The user who is currently logged in.
    :return: The user object of the moved user.
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

    for user_host in user.user_hosts:
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
    :param email: New email address
    :param processor:User object of the processor, which issues the change
    :return:Changed user object
    """
    if not email:
        raise ValueError()
    old_email = user.email
    user.email = email
    message = deferred_gettext(u"Changed e-mail from {} to {}.")
    log_user_event(author=processor, user=user,
                   message=message.format(old_email, email).to_json())
    return user


def traffic_balance(user):
    try:
        bal = user._traffic_balance
        balance = bal.amount
        balance_ts = bal.timestamp
    except AttributeError:
        balance = 0
        balance_ts = datetime.fromtimestamp(0)

    now = session.utcnow()
    if balance_ts > now:
        return None

    # NOTE: if balance timestamp is in future, balance is always None
    #       because consistency cannot be guaranteed

    balance += sum(-event.amount for event in user.traffic_volumes
                   if (balance_ts <= event.timestamp <= now))
    balance += sum(event.amount for event in user.traffic_credits
                   if (balance_ts <= event.timestamp <= now))
    return balance


def traffic_events_expr():
    events = union_all(select([
        TrafficCredit.amount,
        TrafficCredit.user_id,
        TrafficCredit.timestamp,
        literal("credit").label('type')]),

        select([(-TrafficVolume.amount).label('amount'),
                Host.owner_id.label('user_id'),
                TrafficVolume.timestamp,
                literal("debit").label('type')]
               ).select_from(
            TrafficVolume.__table__.join(
                IP.__table__
            ).join(
                Interface.__table__
            ).join(
                Host.__table__)),

        select([TrafficBalance.amount,
                TrafficBalance.user_id.label('user_id'),
                TrafficBalance.timestamp,
                literal("balance").label('type')]  # ).select_from(
               # .__table__.outerjoin(TrafficBalance)
               )
    ).alias('traffic_events')

    return events


def traffic_balance_expr():
    # not a hybrid attribute expression due to circular import dependencies

    balance = select(
        [func.sum(literal_column('traffic_events.amount'))]
    ).select_from(
        traffic_events_expr()
    ).where(
        and_(
            literal_column('traffic_events.user_id') == User.id,
            literal_column('traffic_events.timestamp') <= func.now(),
            literal_column('traffic_events.timestamp') >=
            func.coalesce(
                select([TrafficBalance.timestamp]
                       ).where(
                    TrafficBalance.user_id == User.id
                ).correlate_except(
                    TrafficBalance).as_scalar(),
                datetime.fromtimestamp(0)
            ).label(
                'balance_timestamp'))
    )

    # NOTE: if balance timestamp is in future, balance is always None
    #       since consistency cannot be guaranteed
    return balance.label('traffic_balance')


def has_exceeded_traffic(user):
    """
    The function calculates the balance of the users traffic.
    :param user: The user object which has to be checked.
    :return: True if the user has more traffic than allowed and false if he
    did not exceed the limit.
    """
    return traffic_balance(user) < 0


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


def has_network_access(user):
    """Check if the user is allowed to connect to the network.

    :param user: The user object.

    :return: True if he is allowed to use the network, false if he is
             not.
    """
    return (user.has_property("network_access") and
            not has_exceeded_traffic(user) and
            has_positive_balance(user))


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
def unblock(user, processor):
    """Unblocks a user.

    This removes his membership of the ``config.violation`` group.

    :param User user: The user to be unblocked.
    :param User processor: The admin who unblocked the user.

    :return: The unblocked user.
    """
    remove_member_of(user=user, group=config.violation_group,
                     processor=processor)
    message = deferred_gettext(u"User has been unblocked.")
    log_user_event(message=message.to_json(), author=processor, user=user)
    return user


@with_transaction
def move_out(user, comment, processor, when):
    """
    This function moves out a user and finishes all move_in memberships.
    move_in memberships are parsed from config.
    A log message is created.
    :param User user: The user to move out.
    :param unicode|None comment: An optional comment
    :param User processor: The admin who is going to move out the user.
    :param datetime when: The time the user is going to move out.
    :return: The user that moved out.
    """
    if when > datetime.now():
        raise NotImplementedError("Moving out in the future is not supported yet.")

    for group in (config.member_group, config.network_access_group):
        remove_member_of(user, group, processor, closedopen(when, None))

    num_hosts = 0  # In case the chain is empty
    for num_hosts, h in enumerate(chain(user.user_hosts, user.server_hosts), 1):
        session.session.delete(h)

    user.room = None

    if comment:
        message = deferred_gettext(
            u"Moved out on {} ({} hosts deleted). Comment: {}"
        ).format(when, num_hosts, comment)
    else:
        message = deferred_gettext(
            u"Moved out on {} ({} hosts deleted)."
        ).format(when, num_hosts)

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
        'traffic_exceeded': has_exceeded_traffic(user),
        'network_access': user.has_property('network_access'),
        'account_balanced': user_has_paid(user),
        'violation': user.has_property('violation'),
        'mail': user.has_property('mail'),
        'admin': any(user.has_property(prop) for prop in admin_properties),
    })


def status_query():
    now = single(session.utcnow())
    return session.session.query(
        User,
        User.member_of(config.member_group, now).label('member'),
        # traffic ignored due to pending traffic rework
        literal_column("false").label('traffic_exceeded'),
        (Account.balance < 0).label('account_balanced'),

        # a User.properties hybrid attribute would be preferrable
        (User.has_property('network_access', now)).label('network_access'),
        (User.has_property('violation', now)).label('violation'),
        (User.has_property('mail', now)).label('mail'),
        or_(*(User.has_property(prop, now) for prop in admin_properties)).label('admin')
    ).join(Account)


@with_transaction
def grant_property(group, name):
    """
    Grants a property to a group.

    :param PropertyGroup group: a group
    :param str name: the name of the property
    :return: created or changed property object
    :rtype: Property
    """
    group.property_grants[name] = True
    return group.properties[name]


@with_transaction
def deny_property(group, name):
    """
    Denies a property to a group.

    :param PropertyGroup group: a group
    :param str name: the name of the property
    :return: created or changed property object
    :rtype: Property
    """
    group.property_grants[name] = False
    return group.properties[name]


@with_transaction
def remove_property(group, name):
    """
    Removes a property association (grant or denial) with a given group.

    :param PropertyGroup group: a group
    :param str name: the name of the property
    :raises ValueError: if group doesn't have a property with the given name
    """
    if not group.properties.pop(name, None):
        raise ValueError("Group {0} doesn't have property {1}"
                         .format(group.name, name))


@with_transaction
def make_member_of(user, group, processor, during=UnboundedInterval):
    """
    Makes a user member of a group in a given interval. If the given interval
    overlaps with an existing membership, this method will join the overlapping
    intervals together, so that there will be at most one membership for
    particular user in particular group at any given point in time.

    :param User user: the user
    :param Group group: the group
    :param User processor: User issuing the addition
    :param Interval during:
    """
    memberships = session.session.query(Membership).filter(
        Membership.user == user, Membership.group == group,
        Membership.active(during)).all()
    intervals = IntervalSet(
        closed(m.begins_at, m.ends_at) for m in memberships
    ).union(during)
    for m in memberships:
        session.session.delete(m)
    session.session.add_all(
        Membership(begins_at=i.begin, ends_at=i.end, user=user, group=group)
        for i in intervals)
    message = deferred_gettext(u"Added to group {group} during {during}.")
    log_user_event(message=message.format(group=group.name,
                                          during=during).to_json(),
                   user=user, author=processor)


@with_transaction
def remove_member_of(user, group, processor, during=UnboundedInterval):
    """
    Removes a user from a group in a given interval. The interval defaults to
    the unbounded interval, so that the user will be removed from the group at
    any point in time.

    :param User user: the user
    :param Group group: the group
    :param User processor: User issuing the removal
    :param Interval during:
    """
    memberships = session.session.query(Membership).filter(
        Membership.user == user, Membership.group == group,
        Membership.active(during)).all()
    intervals = IntervalSet(
        closed(m.begins_at, m.ends_at) for m in memberships
    ).difference(during)
    for m in memberships:
        session.session.delete(m)
    session.session.add_all(
        Membership(begins_at=i.begin, ends_at=i.end, user=user, group=group)
        for i in intervals)
    message = deferred_gettext(u"Removed from group {group} during {during}.")
    log_user_event(message=message.format(group=group.name,
                                          during=during).to_json(),
                   user=user, author=processor)
