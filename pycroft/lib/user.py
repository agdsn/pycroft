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

from datetime import datetime, time
import re

from sqlalchemy.sql.expression import func, literal

from pycroft import messages, config
from pycroft.helpers import user, net
from pycroft.helpers.errorcode import Type1Code, Type2Code
from pycroft.helpers.interval import (
    Interval, IntervalSet, UnboundedInterval, closed, closedopen)
from pycroft.lib.host import generate_hostname
from pycroft.lib.net import get_free_ip, select_subnet_for_ip
from pycroft.model.accounting import TrafficVolume
from pycroft.model.dns import ARecord, CNAMERecord
from pycroft.model.facilities import Room
from pycroft.model.finance import FinanceAccount
from pycroft.model.host import Host, Ip, UserHost, UserNetDevice
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import User, Membership, TrafficGroup
from pycroft.lib.logging import log_user_event
from pycroft.lib.finance import get_current_semester, user_has_paid


def encode_type1_user_id(user_id):
    """Append a type-1 error detection code to the user_id."""
    return u"{0:04d}-{1:d}".format(user_id, Type1Code.calculate(user_id))


type1_user_id_pattern = re.compile(ur"^(\d{4,})-(\d)$", re.UNICODE)


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


type2_user_id_pattern = re.compile(ur"^(\d{4,})-(\d{2})$", re.UNICODE)


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


@with_transaction
def move_in(name, login, email, dormitory, level, room_number, mac,
            processor, moved_from_division, already_paid_semester_fee, host_name=None):
    """
    This function creates a new user, assign him to a room and creates some
    initial groups and transactions.
    :param name: The full name of the user. (Max Mustermann)
    :param login: The unix login for the user.
    :param email: E-Mail address of the user.
    :param dormitory: The dormitory the user moves in.
    :param level: The level the user moves in.
    :param room_number: The room number the user moves in.
    :param mac: The mac address of the users pc.
    :param moved_from_division: User was already member of another division
    :param already_paid_semester_fee: User paid at other division for current semester
    :param host_name: An optional Hostname for the users pc.
    :return: The new user object.
    """

    room = Room.q.filter_by(number=room_number,
        level=level, dormitory=dormitory).one()


    now = session.utcnow()
    # create a new user
    new_user = User(
        login=login,
        name=name,
        email=email,
        room=room,
        registered_at=now,
        finance_account=FinanceAccount(name="", type="ASSET")
    )
    plain_password = user.generate_password(12)

    # set random initial password
    new_user.set_password(plain_password)
    session.session.add(new_user)
    account_name = messages['finance']['user_finance_account_name'].format(
        user_id=new_user.id)
    new_user.finance_account.name = account_name

    # create one new host (including net_device) for the new user
    subnets = filter(lambda s: s.ip_type == '4', dormitory.subnets)
    ip_address = get_free_ip(subnets)
    subnet = select_subnet_for_ip(ip_address, subnets)
    #ToDo: Which port to choose if room has more than one?
    # --> The one that is connected to a switch!
    # ---> what if there are two or more ports in one room connected to the switch? (double bed room)
    patch_port = room.patch_ports[0]

    new_host = UserHost(user=new_user, room=room)
    session.session.add(new_host)
    new_net_device = UserNetDevice(mac=mac, host=new_host)
    new_ip = Ip(net_device=new_net_device, address=ip_address, subnet=subnet)
    session.session.add(new_ip)
    new_a_record = ARecord(host=new_host, time_to_live=None,
                           name=generate_hostname(ip_address),
                           address=new_ip)
    session.session.add(new_a_record)
    if host_name:
        session.session.add(CNAMERecord(host=new_host, name=host_name,
                                        record_for=new_a_record))

    for group in (config.member_group, config.network_access_group):
        make_member_of(new_user, group, closed(now, None))

    if moved_from_division:
        group = config.moved_from_division_group
        make_member_of(new_user, group, closedopen(now, None))

    if already_paid_semester_fee:
        group = config.already_paid_semester_fee_group
        during = closed(now, datetime.combine(
            get_current_semester().ends_on, time.max))
        make_member_of(new_user, group, during)

    fees = [
        RegistrationFee(config.registration_fee_account),
        SemesterFee(config.semester_fee_account),
    ]
    # Post initial fees
    post_fees([new_user], fees, processor)

    move_in_user_log_entry = log_user_event(
        author=processor,
        message=messages["move_in"]["log_message"],
        user=new_user
    )

    #TODO: print plain password on paper instead
    print u"new password: " + plain_password

    return new_user


#TODO ensure serializability
@with_transaction
def move(user, dormitory, level, room_number, processor):
    """
    Moves the user into another room.
    :param user: The user to be moved.
    :param dormitory: The new dormitory.
    :param level: The level of the new room.
    :param room_number: The number of the new room.
    :param processor: The user who is currently logged in.
    :return: The user object of the moved user.
    """

    old_room = user.room
    new_room = Room.q.filter_by(
        number=room_number,
        level=level,
        dormitory_id=dormitory.id
    ).one()

    assert old_room != new_room,\
        "A User is only allowed to move in a different room!"

    user.room = new_room

    log_user_event(
        author=processor,
        message=messages["move"]["log_message"].format(
            from_room=old_room, to_room=new_room),
        user=user
    )

    for user_host in user.user_hosts:
        user_host.room = new_room
        net_dev = user_host.user_net_device

        # assign a new IP to each net_device
        if old_room.dormitory_id != new_room.dormitory_id:
            for ip in net_dev.ips:
                old_ip = ip.address
                new_ip = get_free_ip(dormitory.subnets)
                new_subnet = select_subnet_for_ip(new_ip,
                                                       dormitory.subnets)

                ip.change_ip(new_ip, new_subnet)

                log_user_event(
                    author=processor,
                    message=messages["move"]["ip_change_log_message"].format(
                        old_ip=old_ip, new_ip=new_ip),
                    user=user)

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
    log_user_event(author=processor, user=user,
                   message=u"Nutzer {} umbenannt in {}".format(old_name, name))
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
    log_user_event(author=processor, user=user,
                   message=u"E-Mail-Adresse von {} auf {} "
                           u"geändert.".format(old_email, email))
    return user


#ToDo: Usecases überprüfen: standardmäßig nicht False?
def has_exceeded_traffic(user, when=None):
    """
    The function calculates the balance of the users traffic.
    :param user: The user object which has to be checked.
    :return: True if the user has more traffic than allowed and false if he
    did not exceed the limit.
    """
    return session.session.query(
        (
            func.max(TrafficGroup.traffic_limit) * literal(1.10) <
            func.sum(TrafficVolume.size)
        ).label("has_exceeded_traffic")
    ).select_from(
        TrafficGroup
    ).join(
        Membership
    ).join(
        User.user_hosts
    ).join(
        Host.ips
    ).join(
        Ip.traffic_volumes
    ).filter(
        Membership.active(when),
        Membership.user_id == user.id
    ).scalar()

#ToDo: Funktion zur Abfrage dr Kontobilanz
def has_positive_balance(user):
    return True

def has_network_access(user):
    """
    The function evaluates if the user is allowed to connect to the network.
    :param user: The user object.
    :return: True if he is allowed to use the network, false if he is not.
    """
    return (user.has_property("network_access") and
            not has_exceeded_traffic(user) and
            has_positive_balance(user))


@with_transaction
def block(user, reason, processor, during=None):
    """
    This function blocks a user in a given interval by making him a member of
    the violation group in the given interval. A reason should be provided.
    :param User user: The user to be blocked.
    :param unicode reason: The reason of blocking.
    :param User processor: The admin who blocked the user.
    :param Interval|None during: The interval in which the user is blocked. If
    None the user will be blocked from now on without an upper bound.
    :return: The blocked user.
    """
    if during is None:
        during = closedopen(session.utcnow(), None)

    make_member_of(user, config.violation_group, during)

    log_message = messages["block"]["log_message"].format(
        begin=during.begin.strftime("%Y.%m.%d") if during.begin else u'unspezifiert',
        end=during.end.strftime("%Y.%m.%d") if during.end else u'unspezifiert',
        reason=reason)

    log_user_event(message=log_message, author=processor, user=user)

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
    for group in (config.member_group, config.network_access_group):
        remove_member_of(user, group, closedopen(when, None))

    log_message = messages["move_out"]["log_message"].format(
        date=when.strftime("%d.%m.%Y")
    )
    if comment:
        log_message += messages["move_out"]["log_message_comment"].format(
            comment=comment
        )

    log_user_event(
        message=log_message,
        author=processor,
        user=user
    )

    return user


@with_transaction
def move_out_temporarily(user, comment, processor, during=None):
    """
    This function moves a user temporally. A log message is created.
    :param User user: The user to move out.
    :param unicode|None comment: Comment for temp moveout
    :param User processor: The admin who is going to move out the user.
    :param Interval[date]|None during: The interval in which the user is away.
    If None, interval is set from now without an upper bound.
    :return: The user to move out.
    """
    if during is None:
        during = closedopen(session.utcnow(), None)
    make_member_of(user, config.away_group, during)

    #TODO: the ip should be deleted just! if the user moves out now!
    for user_host in user.user_hosts:
        if user_host is not None:
            session.session.delete(user_host.user_net_device.ips[0])

    log_message = messages["move_out_tmp"]["log_message"].format(
        begin=during.begin.strftime("%Y.%m.%d") if during.begin else u'unspezifiert',
        end=during.end.strftime("%Y.%m.%d") if during.end else u'unspezifiert'
    )
    if comment:
        log_message += messages["move_out_tmp"]["log_message_comment"].format(
            comment=comment
        )

    log_user_event(
        message=log_message,
        author=processor,
        user=user
    )

    return user


@with_transaction
def is_back(user, processor):
    """
    After a user moved temporarily out, this function sets group memberships and
     creates a log message
    :param user: The User who is back.
    :param processor: The admin recognizing the users return.
    :return: The user who returned.
    """
    away_group = config.away_group
    remove_member_of(user, away_group, closedopen(session.utcnow(), None))

    subnets = user.room.dormitory.subnets
    ip_address = get_free_ip(subnets)
    subnet = select_subnet_for_ip(ip_address, subnets)

    for user_host in user.user_hosts:
        session.session.add(Ip(
            address=ip_address,
            subnet=subnet,
            net_device=user_host.user_net_device
        ))

    log_user_event(
        message=messages["move_out_tmp"]["log_message_back"],
        author=processor,
        user=user
    )

    return user


def infoflags(user):
    """Returns informational flags regarding the user
    :param User user: User object
    :return: A list of infoflags with a title and a value
    :rtype: list[dict[str, bool]]
    """
    return [
        {'title': u"Internetzugang", 'val': user.has_property("internet")},
        {'title': u"Traffic übrig", 'val': has_exceeded_traffic(user)},
        {'title': u"Bezahlt", 'val': user_has_paid(user)},
        {'title': u"Verstoßfrei", 'val': not user.has_property("violation")},
        {'title': u"Mailkonto", 'val': user.has_property("mail")},
    ]


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
def make_member_of(user, group, during=UnboundedInterval):
    """
    Makes a user member of a group in a given interval. If the given interval
    overlaps with an existing membership, this method will join the overlapping
    intervals together, so that there will be at most one membership for
    particular user in particular group at any given point in time.

    :param User user: the user
    :param Group group: the group
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


@with_transaction
def remove_member_of(user, group, during=UnboundedInterval):
    """
    Removes a user from a group in a given interval. The interval defaults to
    the unbounded interval, so that the user will be removed from the group at
    any point in time.

    :param User user: the user
    :param Group group: the group
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
