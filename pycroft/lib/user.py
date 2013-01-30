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
from pycroft.model.host import Host, UserHost, UserNetDevice, Ip
from pycroft.model.logging import UserLogEntry
from pycroft.model.property import TrafficGroup, Membership, Group, PropertyGroup
from pycroft.model.finance import FinanceAccount, Transaction, Split, Semester
from pycroft.model import session
from pycroft.model.user import User
from pycroft.lib import user_config
from pycroft.lib.host_alias import create_arecord, create_cnamerecord


def moves_in(name, login, email, dormitory, level, room_number, host_name, mac,
             current_semester, processor):
    """
    This function creates a new user, assign him to a room and creates some
    inital groups and transactions.
    :param name: The full name of the user. (Max Mustermann)
    :param login: The unix login for the user.
    :param email: E-Mail address of the user.
    :param dormitory: The dormitory the user moves in.
    :param level: The level the user moves in.
    :param room_number: The room number the user moves in.
    :param host_name: An optional Hostname for the users pc.
    :param mac: The mac address of the users pc.
    :param current_semester: The semester the user moves in.
    :param initial_groups: The groups a user is member from beginning.
    :return: The new user object.
    """

    room = Room.q.filter_by(number=room_number,
        level=level, dormitory_id=dormitory.id).one()

    # create a new user
    new_user = User(login=login,
        name=name,
        email=email,
        room=room,
        registration_date=datetime.now())
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

    new_host = UserHost(user_id = new_user.id, user=new_user,room=room)

    new_net_device = UserNetDevice(mac=mac, host=new_host)
    new_ip = Ip(net_device=new_net_device, address=ip_address, subnet=subnet)

    session.session.add(new_host)
    session.session.add(new_net_device)
    session.session.add(new_ip)

    new_arecord = create_arecord( host=new_host, time_to_live=None, name=host.generate_hostname(ip_address), address=new_ip)
    if host_name:
        create_cnamerecord(host=new_host, name=host_name, alias_for=new_arecord)


    #TODO: add user to initial groups (create those memberships)
    for initial_group in user_config.initial_groups:
        assert isinstance(initial_group["dates"]["start_date"], timedelta)
        assert not initial_group["dates"]["start_date"] < timedelta(0)
        group = Group.q.filter(Group.name == initial_group["group_name"]).one()
        new_membership = Membership(
            start_date=datetime.now() + initial_group["dates"]["start_date"],
            group=group,
            user=new_user)
        if initial_group["dates"]["end_date"] is 0:
            assert not initial_group["dates"]["end_date"] < 0
        else:
            assert isinstance(initial_group["dates"]["end_date"], timedelta)
            assert not initial_group["dates"]["end_date"] < timedelta(0)
            new_membership.end_date = datetime.now() + initial_group["dates"][
                                                     "end_date"]

    registration_fee_account = FinanceAccount.q.filter(
        FinanceAccount.name == u"Anmeldegebühren").one()
    semester_fee_account = FinanceAccount.q.filter(
        FinanceAccount.name == u"Beiträge").one()


    #TODO: create financial account for user with negative balance
    #adds the initial finance transactions to the user
    new_finance_account = FinanceAccount(name=u"Nutzerid: %i" % new_user.id,
        type="EQUITY", user=new_user)
    #Transaction for the registration fee
    new_transaction_registration_fee = Transaction(
        message=u"Anmeldegebühren bei der AG DSN von Nutzer %s" % (
            new_user.id, ), transaction_date=datetime.now(),
        semester=current_semester)
    #Transaction for the semester fee
    new_transaction_semester_fee = Transaction(
        message=u"Semestergebühren für das Semester %s von Nutzer %s" % (
            current_semester.name, new_user.id),
        transaction_date=datetime.now(), semester=current_semester)
    #soll per Nutzerkonto
    new_split_registration_user = Split(amount=current_semester.registration_fee,
        account=new_finance_account,
        transaction=new_transaction_registration_fee)
    #haben an Anmeldegebühren
    new_split_registration_ag = Split(amount=-current_semester.registration_fee,
        account=registration_fee_account,
        transaction=new_transaction_registration_fee)
    #soll per Nutzerkonto
    new_split_semester_user = Split(amount=current_semester.semester_fee,
        account=new_finance_account,
        transaction=new_transaction_semester_fee)
    #haben an Beiträge
    new_split_semester_ag = Split(amount=-current_semester.semester_fee,
        account=semester_fee_account,
        transaction=new_transaction_semester_fee)

    finance_things = [new_finance_account, new_transaction_registration_fee,
        new_transaction_semester_fee, new_split_registration_user,
        new_split_registration_ag, new_split_semester_user,
        new_split_semester_ag]

    session.session.add_all(finance_things)

    #TODO: add membership that allows negative account balance for one month

    move_in_user_log_entry = UserLogEntry(author_id=processor.id,
        message=u"angemeldet" , timestamp=datetime.now(), user_id=new_user.id)
    session.session.add(move_in_user_log_entry)

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
    new_room = Room.q.filter_by(number=room_number,
        level=level,
        dormitory_id=dormitory.id).one()

    assert old_room is not new_room, "A User is only allowed to move in a different room!"

    user.room = new_room
    session.session.add(user)

    moving_user_log_entry = UserLogEntry(author_id=processor.id,
        message=u"umgezogen von %s nach %s" % (old_room, new_room),
        timestamp=datetime.now(), user_id=user.id)
    session.session.add(moving_user_log_entry)

    # assign a new IP to each net_device
    net_dev = user.user_host.user_net_device

    if old_room.dormitory_id != new_room.dormitory_id:
        assert len(net_dev.ips) == 1, u"A user should only have one ip!"
        ip_addr = net_dev.ips[0]
        old_ip = ip_addr.address
        new_address = host.get_free_ip(dormitory.subnets)
        new_subnet = host.select_subnet_for_ip(new_address,
                                            dormitory.subnets)

        ip_addr.change_ip(new_address, new_subnet)

        ip_change_log_entry = UserLogEntry(author_id=processor.id,
            message=u"IPv4 von %s auf %s geändert" % (
            old_ip, new_address),
            timestamp=datetime.now(), user_id=user.id)
        session.session.add(ip_change_log_entry)

    #TODO set new PatchPort for each NetDevice in each Host that moves to the new room
    #moves the host in the new room and assign the belonging net_device to the new patch_port
    user.user_host.room = new_room

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

        newUserLogEntry = UserLogEntry(author_id=processor.id,
            message=u"Nutzer %s umbenannt in %s" % (oldName, name),
            timestamp=datetime.now(), user_id=user.id)
        session.session.add(newUserLogEntry)

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

        logEntry = UserLogEntry(author_id=processor.id,
            message=u"E-Mail-Adresse von %s auf %s geändert." % (oldEmail, email),
            timestamp=datetime.now(), user_id=user.id)
        session.session.add(logEntry)
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
    result = session.session.query(User.id,
        (func.max(TrafficGroup.traffic_limit) * 1.10) < func.sum(
            TrafficVolume.size).label("has_exceeded_traffic")).join(
        User.active_traffic_groups).join(User.user_host).join(Host.ips).join(
        Ip.traffic_volumes).filter(User.id == user.id).group_by(User.id).first()
    if result is not None:
        return result.has_exceeded_traffic
    else: return False

#ToDo: Funktion zur Abfrage dr Kontobilanz
def has_positive_balance(user):
    return True

def has_internet(user):
    """
    The function evaluates if the user is allowed to connect to the internet.
    :param user: The user object.
    :return: True if he is allowed to use the internet, false if he is not.
    """
    if user.has_property("internet"):
        if user.has_property("no_internet"):
            return False
        else:
            if has_exceeded_traffic(user):
                return False
            else:
                if has_positive_balance(user):
                    return True
                else:
                    return False
    else:
        return False

def ban_user(user, date, reason, processor):
    """
    This function bans a user for a certain time.
    A logmessage with a reason is created.
    :param user: The user to be banned.
    :param date: The date the user is not banned anymore.
    :param reason: The reason of banning.
    :param processor: The admin who banned the user.
    :return: The banned user.
    """

    ban_group = PropertyGroup.q.filter(PropertyGroup.name==u"Verstoß").one()

    new_membership = Membership(end_date=datetime.combine(date, time(0)),
        group=ban_group,
        user=user)

    ban_message = u"Sperrung bis zum %s: %s" % (
        date.strftime("%d.%m.%Y"), reason)

    new_log_entry = UserLogEntry(message=ban_message,
        timestamp=datetime.now(),
        author=processor,
        user=user)

    session.session.add(new_membership)
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
    for membership in user.memberships:
        if membership.end_date is None:
            membership.end_date = date
        if membership.end_date > date:
            membership.end_date = date

    if(comment):
        log_message = user.name + " wird zum " + date.strftime("%d.%m.%Y") + " komplett ausziehen. Kommentar: " + comment
    else:
        log_message = user.name + " wird zum " + date.strftime("%d.%m.%Y") + " komplett ausziehen."
    new_log_entry = UserLogEntry(message=log_message,
        timestamp=datetime.now(),
        author=processor,
        user=user)
    session.session.add(new_log_entry)
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
        PropertyGroup.name == u"tmpAusgezogen").one()

    new_membership = Membership(group=away_group, user=user)

    user.is_away = True

    session.session.delete(user.user_host.user_net_device.ips[0])

    if comment:
        log_message = user.name + " wird zum " + date.strftime("%d.%m.%Y") + " temporaer ausziehen. Kommentar: " + comment
    else:
        log_message = user.name + " wird zum " + date.strftime("%d.%m.%Y") + " temporaer ausziehen."
    new_log_entry = UserLogEntry(message=log_message,
        timestamp=datetime.now(),
        author=processor,
        user=user)
    session.session.add(new_log_entry)
    session.session.commit()
    return user