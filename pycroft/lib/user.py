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

from sqlalchemy import and_, exists, func, literal

from pycroft import config, property
from pycroft.helpers import user, AttrDict
from pycroft.helpers.errorcode import Type1Code, Type2Code
from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.interval import (
    Interval, IntervalSet, UnboundedInterval, closed, closedopen)
from pycroft.lib.accounting import grant_traffic, has_exceeded_traffic
from pycroft.lib.host import generate_hostname
from pycroft.lib.net import get_free_ip, ptr_name
from pycroft.model.accounting import TrafficVolume
from pycroft.model.dns import AddressRecord, CNAMERecord, DNSName, PTRRecord
from pycroft.model.facilities import Room
from pycroft.model.finance import Account
from pycroft.model.host import Host, IP, UserHost, UserInterface
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


class HostAliasExists(ValueError):
    pass


def setup_ipv4_networking(host):
    subnets = filter(lambda s: s.address.version == 4,
                     [p.switch_interface.default_subnet
                      for p in host.room.switch_patch_ports
                      if p.switch_interface is not None])
    for interface in host.user_interfaces:
        ip_address, subnet = get_free_ip(subnets)
        new_ip = IP(interface=interface, address=ip_address,
                    subnet=subnet)
        session.session.add(new_ip)
        address_record_name = DNSName(name=generate_hostname(ip_address),
                                      zone=subnet.primary_dns_zone)
        session.session.add(AddressRecord(name=address_record_name,
                                          address=new_ip))
        ptr_record_name = DNSName(name=ptr_name(subnet.address, ip_address),
                                  zone=subnet.reverse_dns_zone)
        session.session.add(ptr_record_name)
        session.session.add(PTRRecord(name=ptr_record_name,
                                      address_id=new_ip.id,
                                      ptrdname=address_record_name))
        if host.desired_name:
            name_exists = session.session.query(
                exists().where(and_(DNSName.name == host.desired_name,
                                    DNSName.zone == config.user_zone))).scalar()
            if name_exists:
                raise HostAliasExists()
            cname_record_name = DNSName(name=host.desired_name,
                                        zone=config.user_zone)
            session.session.add(CNAMERecord(name=cname_record_name,
                                            cname=address_record_name))


@with_transaction
def move_in(name, login, email, building, level, room_number, mac,
            processor, moved_from_division, already_paid_semester_fee, host_name=None):
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
    # create a new user
    new_user = User(
        login=login,
        name=name,
        email=email,
        room=room,
        registered_at=now,
        account=Account(name="", type="USER_ASSET")
    )
    plain_password = user.generate_password(12)

    # set random initial password
    new_user.set_password(plain_password)
    with session.session.begin(subtransactions=True):
        session.session.add(new_user)
    new_user.account.name = deferred_gettext(u"User {id}").format(
        id=new_user.id).to_json()

    # create one new host (including interface) for the new user
    new_host = UserHost(owner=new_user, room=room, desired_name=host_name)
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
    If the host changes subnet, it will get a new IP address and existing CNAME
    records will point to the primary name of the new address.
    :param UserHost host: Host to be migrated
    :param Room new_room: new room of the host
    :param User processor: User processing the migration
    :return:
    """
    old_room = host.room
    host.room = new_room
    subnets = [p.switch_interface.default_subnet
               for p in new_room.switch_patch_ports
               if p.switch_interface.default_subnet is not None]
    if old_room.building_id == new_room.building_id:
        return
    for interface in host.user_interfaces:
        old_ips = tuple(ip for ip in interface.ips)
        for old_ip in old_ips:
            ip_address, subnet = get_free_ip(subnets)
            new_ip = IP(interface=interface, address=ip_address,
                        subnet=subnet)
            session.session.add(new_ip)
            address_record_name = DNSName(name=generate_hostname(ip_address),
                                          zone=subnet.primary_dns_zone)
            session.session.add(address_record_name)
            session.session.add(AddressRecord(name=address_record_name,
                                              address=new_ip))
            # Migrate existing CNAME records
            cname_target_ids = frozenset(r.name.id
                                         for r in old_ip.address_records)
            if cname_target_ids:
                cnames = CNAMERecord.q.filter(CNAMERecord.cname_id.in_(
                    cname_target_ids
                ))
                for cname_record in cnames:
                    cname_record.cname = address_record_name
            ptr_record_name = DNSName(name=ptr_name(subnet.address, ip_address),
                                      zone=subnet.reverse_dns_zone)
            session.session.add(ptr_record_name)
            session.session.add(PTRRecord(name=ptr_record_name,
                                          address_id=new_ip.id,
                                          ptrdname=address_record_name))
            old_address = old_ip.address
            session.session.delete(old_ip)

            message = deferred_gettext(u"Changed IP from {} to {}.").format(
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


def is_member(user):
    """Check whether the given user is a member right now."""
    return config.member_group in user.active_property_groups()


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
    """
    The function evaluates if the user is allowed to connect to the network.

    :param user: The user object.
    :return: True if he is allowed to use the network, false if he is not.
    """
    # ToDo JanLo: Kill the has_exceeded_traffic from here to support throttling
    return (user.has_property("network_access") and
            not has_exceeded_traffic(user) and
            has_positive_balance(user))


@with_transaction
def suspend(user, reason, processor, during=None):
    """
    This function suspends a user in a given interval by making him a member of
    the violation group in the given interval. A reason should be provided.
    :param User user: The user to be suspended.
    :param unicode reason: The reason for suspending.
    :param User processor: The admin who suspended the user.
    :param Interval|None during: The interval in which the user is suspended.
    If None the user will be suspendeded from now on without an upper bound.
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
        remove_member_of(user, group, processor, closedopen(when, None))

    if comment:
        message = deferred_gettext(u"Moved out on {}. Comment: {}").format(
            when, comment)
    else:
        message = deferred_gettext(u"Moved out on {}.").format(when)

    log_user_event(
        message=message.to_json(),
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
    make_member_of(user, config.away_group, processor, during)

    #TODO: the ip should be deleted just! if the user moves out now!
    for user_host in user.user_hosts:
        for interface in user_host.user_interfaces:
            for ip in interface.ips:
                session.session.delete(ip)

    if comment:
        message = deferred_gettext(u"Moved out temporarily during {during}. "
                                   u"Comment: {comment}").format(
            during=during, comment=comment)
    else:
        message = deferred_gettext(u"Moved out temporarily {during}.").format(
            during=during)

    log_user_event(message=message.to_json(), author=processor, user=user)
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
    remove_member_of(user, away_group, processor,
                     closedopen(session.utcnow(), None))

    for user_host in user.user_hosts:
        setup_ipv4_networking(user_host)

    log_user_event(message=deferred_gettext(u"Moved back in.").to_json(),
                   author=processor, user=user)
    return user


admin_properties = property.property_categories[u"Nutzerverwaltung"].keys()


def status(user):
    """
    :param user: User whose status we want to look at
    :return: dict of boolean status codes
    """
    return AttrDict({
        'member': is_member(user),
        'traffic_exceeded': has_exceeded_traffic(user),
        'network_access': user.has_property('network_access'),
        'account_balanced': user_has_paid(user),
        'violation': user.has_property('violation'),
        'mail': user.has_property('mail'),
        'admin': any(user.has_property(prop) for prop in admin_properties),
    })


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
