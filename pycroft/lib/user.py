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

from datetime import datetime, time, timedelta
import re

from sqlalchemy.sql.expression import func, literal

from pycroft import config
from pycroft.helpers import user, host
from pycroft.helpers.errorcode import Type1Code, Type2Code
from pycroft.model.accounting import TrafficVolume
from pycroft.model.dns import ARecord, CNAMERecord
from pycroft.model.dormitory import Room
from pycroft.model.finance import FinanceAccount
from pycroft.model.host import Host, Ip, UserHost, UserNetDevice
from pycroft.model.property import TrafficGroup, Membership, Group, PropertyGroup
from pycroft.model import session
from pycroft.model.session import with_transaction
from pycroft.model.user import User
from pycroft.lib.property import create_membership
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
    account_name = config['finance']['user_finance_account_name'].format(
        user_id=new_user.id)
    new_user.finance_account.name = account_name

    # create one new host (including net_device) for the new user
    subnets = dormitory.subnets
    ip_address = host.get_free_ip(subnets)
    subnet = host.select_subnet_for_ip(ip_address, subnets)
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
                           name=host.generate_hostname(ip_address),
                           address=new_ip)
    session.session.add(new_a_record)
    if host_name:
        session.session.add(CNAMERecord(host=new_host, name=host_name,
                                        record_for=new_a_record))

    conf = config["move_in"]

    for membership in conf["default_group_memberships"]:
        group = Group.q.filter(Group.name == membership["name"]).one()
        begins_at = now + timedelta(membership.get("offset", 0))
        ends_at = None
        if membership.get("duration"):
            assert membership["duration"] > 0
            ends_at = begins_at + timedelta(membership["duration"])
        new_membership = create_membership(
            begins_at=begins_at,
            ends_at=ends_at,
            group=group,
            user=new_user
        )

    if moved_from_division:
        for membership in conf["moved_from_division"]:
            group = Group.q.filter(Group.name == membership["name"]).one()
            create_membership(
                begins_at=now,
                ends_at=None,
                group=group,
                user=new_user
            )

    if already_paid_semester_fee:
        for membership in conf["already_paid_semester_fee"]:
            group = Group.q.filter(Group.name == membership["name"]).one()
            create_membership(
                begins_at=now,
                ends_at=datetime.combine(get_current_semester().ends_on, time.min),
                group=group,
                user=new_user
        )

    fees = [
        RegistrationFee(FinanceAccount.q.get(
            config["finance"]["registration_fee_account_id"]
        )),
        SemesterFee(FinanceAccount.q.get(
            config["finance"]["semester_fee_account_id"]
        )),
    ]
    # Post initial fees
    post_fees([new_user], fees, processor)

    move_in_user_log_entry = log_user_event(
        author=processor,
        message=conf["log_message"],
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
        message=config["move"]["log_message"].format(
            from_room=old_room, to_room=new_room),
        user=user
    )

    # assign a new IP to each net_device
    for user_host in user.user_hosts:
        net_dev = user_host.user_net_device

        if old_room.dormitory_id != new_room.dormitory_id:
            assert len(net_dev.ips) == 1, "A user should only have one ip!"
            ip_addr = net_dev.ips[0]
            old_ip = ip_addr.address
            new_ip = host.get_free_ip(dormitory.subnets)
            new_subnet = host.select_subnet_for_ip(new_ip,
                                                   dormitory.subnets)

            ip_addr.change_ip(new_ip, new_subnet)

            log_user_event(
                author=processor,
                message=config["move"]["ip_change_log_message"].format(
                    old_ip=old_ip, new_ip=new_ip),
                user=user)

    #TODO set new PatchPort for each NetDevice in each Host that moves to the new room
    #moves the host in the new room and assign the belonging net_device to the new patch_port
    for user_host in user.user_hosts:
        user_host.room = new_room

    return user


@with_transaction
def edit_name(user, name, processor):
    """
    Changes the name of the user and creates a log entry.
    :param user: The user object.
    :param name: The new full name.
    :return: The changed user object.
    """
    oldName = user.name
    if len(name):
        user.name = name

        log_user_event(
            author=processor,
            message=u"Nutzer {} umbenannt in {}".format(oldName, name),
            user=user)

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
    oldEmail = user.email
    if len(email):
        user.email = email

        log_user_event(
            author=processor,
            message=u"E-Mail-Adresse von {} auf {} geändert.".format(oldEmail, email),
            user=user)

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
def block(user, reason, processor, when=None):
    """
    This function blocks a user for a certain time.
    A logmessage with a reason is created.
    :param user: The user to be blocked.
    :param when: The when the user is not blocked anymore.
    :param reason: The reason of blocking.
    :param processor: The admin who blocked the user.
    :return: The blocked user.
    """
    if when is not None and not isinstance(when, datetime):
        raise ValueError("Date should be a datetime object")

    now = session.utcnow()
    if when is not None and when < now:
        raise ValueError("Date should be in the future")

    block_group = PropertyGroup.q.filter(
        PropertyGroup.name == config["block"]["group"]
    ).one()

    if when is not None:
        create_membership(begins_at=now, ends_at=when,
                          group=block_group, user=user)
        log_message = config["block"]["log_message_with_enddate"].format(
            date=when.strftime("%d.%m.%Y"), reason=reason)
    else:
        create_membership(begins_at=now, ends_at=None,
                          group=block_group, user=user)
        log_message = config["block"]["log_message_without_enddate"].format(
            reason=reason)

    log_user_event(message=log_message, author=processor, user=user)

    return user


@with_transaction
def move_out(user, date, comment, processor):
    """
    This function moves out a user and finishes all move_in memberships.
    move_in memberships are parsed from config.
    A log message is created.
    :param user: The user to move out.
    :param date: The date the user is going to move out.
    :param processor: The admin who is going to move out the user.
    :return: The user to move out.
    """
    if not isinstance(date, datetime):
        raise ValueError("Date should be a datetime object!")

    move_in_groups = config["move_in"]["default_group_memberships"]
    for membership in user.memberships:
        if membership.active():
            for move_in_group in move_in_groups:
                if move_in_group["name"] == membership.group.name:
                    membership.ends_at = when


    log_message = config["move_out"]["log_message"].format(
        date=date.strftime("%d.%m.%Y")
    )
    if comment:
        log_message += config["move_out"]["log_message_comment"].format(
            comment=comment
        )

    log_user_event(
        message=log_message,
        author=processor,
        user=user
    )

    return user


@with_transaction
def move_out_tmp(user, date, comment, processor):
    """
    This function moves a user temporally. A log message is created.
    :param user: The user to move out.
    :param date: The date the user is going to move out.
    :param comment: Comment for temp moveout
    :param processor: The admin who is going to move out the user.
    :return: The user to move out.
    """

    if not isinstance(date, datetime):
        raise ValueError("Date should be a datetime object!")

    away_group = PropertyGroup.q.filter(
        PropertyGroup.name == config["move_out_tmp"]["group"]
    ).one()

    tmp_memberships = Membership.q.join(PropertyGroup).filter(
        PropertyGroup.id == away_group.id).all()

    if len(tmp_memberships) > 0:
        # change the existing memberships for tmp_move_out
        for membership in tmp_memberships:
            membership.ends_at = None
            membership.begins_at = when
    else:
        # if there is no move out membership for the user jet, create one
        create_membership(group=away_group, user=user, begins_at=when,
                          ends_at=None)

    #TODO: the ip should be deleted just! if the user moves out now!
    for user_host in user.user_hosts:
        if user_host is not None:
            session.session.delete(user_host.user_net_device.ips[0])

    log_message = config["move_out_tmp"]["log_message"].format(
        date=date.strftime("%d.%m.%Y")
    )
    if comment:
        log_message += config["move_out_tmp"]["log_message_comment"].format(
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
    membership = Membership.q.join(
        (PropertyGroup, Membership.group_id == PropertyGroup.id)
    ).filter(
        PropertyGroup.name == config["move_out_tmp"]["group"],
        Membership.user_id == user.id,
        Membership.active()
    ).one()

    membership.disable()

    subnets = user.room.dormitory.subnets
    ip_address = host.get_free_ip(subnets)
    subnet = host.select_subnet_for_ip(ip_address, subnets)

    for user_host in user.user_hosts:
        session.session.add(Ip(
            address=ip_address,
            subnet=subnet,
            net_device=user_host.user_net_device
        ))

    log_user_event(
        message=config["move_out_tmp"]["log_message_back"],
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
