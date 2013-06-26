# -*- coding: utf-8 -*-
"""
pycroft.lib.user
~~~~~~~~~~~~~~

This module contains.

:copyright: (c) 2012 by AG DSN.
"""

from datetime import datetime, timedelta, time
from flask.ext.login import current_user
from sqlalchemy.sql.expression import func
from pycroft.helpers import user, host
from pycroft.model.accounting import TrafficVolume
from pycroft.model.dormitory import Dormitory, Room, Subnet, VLan
from pycroft.model.host import Host, Ip
from pycroft.model.property import TrafficGroup, Membership, Group, PropertyGroup
from pycroft.model.finance import FinanceAccount, Transaction, Split, Semester
from pycroft.model import session
from pycroft.model.user import User
from pycroft.lib.host_alias import create_arecord, create_cnamerecord
from pycroft.lib.host import create_user_net_device, create_user_host, create_ip
from pycroft.lib.property import create_membership
from pycroft.lib.logging import create_user_log_entry
from pycroft.lib.config import config
from pycroft.lib.finance import simple_transaction


def move_in(name, login, email, dormitory, level, room_number, mac,
             current_semester, processor, host_name=None):
    """
    This function creates a new user, assign him to a room and creates some
    inital groups and transactions.
    :param name: The full name of the user. (Max Mustermann)
    :param login: The unix login for the user.
    :param email: E-Mail address of the user.
    :param dormitory: The dormitory the user moves in.
    :param level: The level the user moves in.
    :param room_number: The room number the user moves in.
    :param mac: The mac address of the users pc.
    :param current_semester: The semester the user moves in.
    :param initial_groups: The groups a user is member from beginning.
    :param host_name: An optional Hostname for the users pc.
    :return: The new user object.
    """

    room = Room.q.filter_by(number=room_number,
        level=level, dormitory=dormitory).one()

    # create a new user
    new_user = User(
        login=login,
        name=name,
        email=email,
        room=room,
        registration_date=datetime.now()
    )
    plain_password = user.generatePassword(12)

    #TODO: print plain password on paper instead
    print u"new password: " + plain_password

    # set random initial password
    new_user.set_password(plain_password)
    session.session.add(new_user)

    # create one new host (including net_device) for the new user
    subnets = dormitory.subnets
    ip_address = host.get_free_ip(subnets)
    subnet = host.select_subnet_for_ip(ip_address, subnets)
    #ToDo: Which port to choose if room has more than one?
    # --> The one that is connected to a switch!
    # ---> what if there are two or more ports in one room connected to the switch? (double bed room)
    patch_port = room.patch_ports[0]

    new_host = create_user_host(user_id=new_user.id, room_id=room.id)
    new_net_device = create_user_net_device(mac=mac, host_id=new_host.id)
    new_ip = create_ip(net_device_id=new_net_device.id, address=ip_address,
                       subnet_id=subnet.id)

    new_arecord = create_arecord(host_id=new_host.id, time_to_live=None,
                                 name=host.generate_hostname(ip_address),
                                 address_id=new_ip.id)
    if host_name:
        create_cnamerecord(host_id=new_host.id, name=host_name,
                           alias_for_id=new_arecord.id)

    conf = config["move_in"]
    for membership in conf["group_memberships"]:
        group = Group.q.filter(Group.name == membership["name"]).one()
        start_date = datetime.now()
        if membership.get("offset"):
            start_date += timedelta(membership["offset"])
        new_membership = create_membership(
            start_date=start_date,
            end_date=None,
            group_id=group.id,
            user_id=new_user.id,
            commit=False)
        if membership.get("duration"):
            assert membership["duration"] > 0
            new_membership.end_date = datetime.now() + timedelta(membership["duration"])

    registration_fee_account = FinanceAccount.q.filter(
        FinanceAccount.semester == current_semester,
        FinanceAccount.tag == "registration_fee").one()
    semester_fee_account = FinanceAccount.q.filter(
        FinanceAccount.semester == current_semester,
        FinanceAccount.tag == "regular_fee").one()


    format_args = {
        "user_id": new_user.id,
        "user_name": new_user.name,
        "semester": current_semester.name
    }
    new_finance_account = FinanceAccount(
        name=conf["financeaccount_name"].format(**format_args),
        type="EQUITY", user=new_user)
    session.session.add(new_finance_account)

    # Initial fees
    simple_transaction(
        conf["registration_fee_message"].format(**format_args),
        new_finance_account,
        registration_fee_account,
        current_semester,
        current_semester.registration_fee,
        commit=False
    )
    simple_transaction(
        conf["semester_fee_message"].format(**format_args),
        new_finance_account,
        semester_fee_account,
        current_semester,
        current_semester.semester_fee,
        commit=False
    )

    move_in_user_log_entry = create_user_log_entry(
        author_id=processor.id,
        message=conf["log_message"],
        timestamp=datetime.now(),
        user_id=new_user.id,
        commit=False
    )

    session.session.commit()

    return new_user


#TODO ensure serializability
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

    assert old_room is not new_room,\
        "A User is only allowed to move in a different room!"

    user.room = new_room

    create_user_log_entry(
        author_id=processor.id,
        message=config["move"]["log_message"].format(
            from_room=old_room, to_room=new_room),
        timestamp=datetime.now(), user_id=user.id,
        commit=False
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

            create_user_log_entry(author_id=processor.id,
                message=config["move"]["ip_change_log_message"].format(
                    old_ip=old_ip, new_ip=new_ip),
                timestamp=datetime.now(), user_id=user.id,
                commit=False)

    #TODO set new PatchPort for each NetDevice in each Host that moves to the new room
    #moves the host in the new room and assign the belonging net_device to the new patch_port
    for user_host in user.user_hosts:
        user_host.room = new_room

    session.session.commit()
    return user


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

        create_user_log_entry(author_id=processor.id,
            message=u"Nutzer %s umbenannt in %s" % (oldName, name),
            timestamp=datetime.now(), user_id=user.id,
            commit=False)

        session.session.commit()

    return user


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

        create_user_log_entry(author_id=processor.id,
            message=u"E-Mail-Adresse von %s auf %s geändert." % (oldEmail, email),
            timestamp=datetime.now(), user_id=user.id,
            commit=False)
        session.session.commit()

    return user


#ToDo: Usecases überprüfen: standardmäßig nicht False?
def has_exceeded_traffic(user):
    """
    The function calculates the balance of the users traffic.
    :param user: The user object which has to be checked.
    :return: True if the user has more traffic than allowed and false if he
    did not exceed the limit.
    """
    result = session.session.query(
        User.id,
        (func.max(TrafficGroup.traffic_limit) * 1.10) < func.sum(TrafficVolume.size).label("has_exceeded_traffic")
    ).join(
        User.active_traffic_groups
    ).join(
        User.user_hosts
    ).join(
        Host.ips
    ).join(
        Ip.traffic_volumes
    ).filter(
        User.id == user.id
    ).group_by(
        User.id
    ).first()

    if result is not None:
        return result.has_exceeded_traffic
    else:
        return False


def has_balance_of_at_least(user, amount):
    """Check whether the given user's balance is at least the given
    amount.

    If a user does not have an account, we treat his balance as if it
    were exactly zero.

    :param user: The user we are interested in.
    :param amount: The amount we want to check for.
    :return: True if and only if the user's balance is at least the given
    amount (and False otherwise).

    """
    if user.finance_account is None:
        return amount <= 0

    balance = session.session.query(
        func.sum(Split.amount)
    ).filter(
        Split.account_id == user.finance_account.id
    ).scalar()

    if balance is None:
        balance = 0

    return balance >= amount


def has_positive_balance(user):
    """Check whether the given user's balance is (weakly) positive.

    :param user: The user we are interested in.
    :return: True if and only if the user's balance is at least zero.

    """
    return has_balance_of_at_least(user, amount=0)


def has_internet(user):
    """
    The function evaluates if the user is allowed to connect to the internet.
    :param user: The user object.
    :return: True if he is allowed to use the internet, false if he is not.
    """
    return user.has_property("internet") and not has_exceeded_traffic(user) \
        and has_positive_balance(user)


def block(user, reason, processor, date=None):
    """
    This function blocks a user for a certain time.
    A logmessage with a reason is created.
    :param user: The user to be blocked.
    :param date: The date the user is not blocked anymore.
    :param reason: The reason of blocking.
    :param processor: The admin who blocked the user.
    :return: The blocked user.
    """
    if date is not None and not isinstance(date, datetime):
        raise ValueError("Date should be a datetime object")

    if date is not None and date < datetime.now():
        raise ValueError("Date should be in the future")

    block_group = PropertyGroup.q.filter(
        PropertyGroup.name == config["block"]["group"]
    ).one()

    if date is not None:
        create_membership(start_date=datetime.now(), end_date=date,
                          group_id=block_group.id, user_id=user.id,
                          commit=False)
        log_message = config["block"]["log_message_with_enddate"].format(
            date=date.strftime("%d.%m.%Y"), reason=reason)
    else:
        create_membership(start_date=datetime.now(), end_date=None,
                          group_id=block_group.id, user_id=user.id,
                          commit=False)
        log_message = config["block"]["log_message_without_enddate"].format(
            reason=reason)

    create_user_log_entry(message=log_message, timestamp=datetime.now(),
                          author_id=processor.id, user_id=user.id,
                          commit=False)

    session.session.commit()
    return user


def move_out(user, date, comment, processor):
    """
    This function moves out a user and finishes all his memberships. A logmessage is created.
    :param user: The user to move out.
    :param date: The date the user is going to move out.
    :param processor: The admin who is going to move out the user.
    :return: The user to move out.
    """
    if not isinstance(date,datetime):
        raise ValueError("Date should be a datetime object!")

    for membership in user.memberships:
        if membership.end_date is None or membership.end_date > date:
            if membership.start_date > date:
                membership.end_date = membership.start_date
            else:
                membership.end_date = date

    log_message = config["move_out"]["log_message"].format(
        date=date.strftime("%d.%m.%Y")
    )
    if comment:
        log_message += config["move_out"]["log_message_comment"].format(
            comment=comment
        )

    create_user_log_entry(
        message=log_message,
        timestamp=datetime.now(),
        author_id=processor.id,
        user_id=user.id,
        commit=False
    )

    session.session.commit()
    return user


def move_out_tmp(user, date, comment, processor):
    """
    This function moves a user temporally. A logmessage is created.
    :param user: The user to move out.
    :param date: The date the user is going to move out.
    :param comment: Comment for temp moveout
    :param processor: The admin who is going to move out the user.
    :return: The user to move out.
    """
    away_group = PropertyGroup.q.filter(
        PropertyGroup.name == config["move_out_tmp"]["group"]
    ).one()

    if not isinstance(date, datetime):
        raise ValueError("Date should be a datetime object!")

    create_membership(group_id=away_group.id, user_id=user.id, start_date=date,
                      end_date=None, commit=False)

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

    create_user_log_entry(
        message=log_message,
        timestamp=datetime.now(),
        author_id=processor.id,
        user_id=user.id,
        commit=False
    )

    session.session.commit()

    return user


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
        Membership.active
    ).one()

    membership.disable()

    subnets = user.room.dormitory.subnets
    ip_address = host.get_free_ip(subnets)
    subnet = host.select_subnet_for_ip(ip_address, subnets)

    for user_host in user.user_hosts:
        create_ip(
            address=ip_address,
            subnet_id=subnet.id,
            net_device_id=user_host.user_net_device.id,
            commit=False
        )

    create_user_log_entry(
        message=config["move_out_tmp"]["log_message_back"],
        timestamp=datetime.now(),
        author_id=processor.id,
        user_id=user.id,
        commit=False
    )

    session.session.commit()

    return user
