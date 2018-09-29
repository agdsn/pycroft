# -*- coding: utf-8 -*-
# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.logging import log_user_event
from pycroft.lib.net import get_subnets_for_room, get_free_ip
from pycroft.lib.user import migrate_user_host
from pycroft.model.host import Interface, IP, Host
from pycroft.model.session import with_transaction, session


@with_transaction
def change_mac(interface, mac, processor):
    """
    This method will change the mac address of the given interface to the new
    mac address.

    :param interface: the interface which should become a new mac address.
    :param mac: the new mac address.
    :param processor: the user who initiated the mac address change.
    :return: the changed interface with the new mac address.
    """
    old_mac = interface.mac
    interface.mac = mac
    message = deferred_gettext(u"Changed MAC address from {} to {}.").format(
        old_mac, mac)
    log_user_event(message.to_json(), processor, interface.host.owner)
    return interface


def generate_hostname(ip_address):
    """

    :param IPv4Address ip_address:
    :rtype: unicode
    :return:
    """
    numeric_ip = int(ip_address)
    return u"x{0:02x}{1:02x}{2:02x}{3:02x}".format((numeric_ip >> 0x18) & 0xFF,
                                                   (numeric_ip >> 0x10) & 0xFF,
                                                   (numeric_ip >> 0x08) & 0xFF,
                                                   (numeric_ip >> 0x00) & 0xFF)


@with_transaction
def host_create(owner, room, name, processor):
    host = Host(name=name,
                owner_id=owner.id,
                room=room)

    session.add(host)

    message = deferred_gettext(
        u"Created host '{name}' in {dorm} {level}-{room}."
        .format(name=host.name,
                dorm=room.building.short_name,
                level=room.level,
                room=room.number))

    log_user_event(author=processor,
                   user=owner,
                   message=message.to_json())\

    return host


@with_transaction
def host_edit(host, owner, room, name, processor):
    if host.owner_id != owner.id:
        message = deferred_gettext(
            u"Transferred Host '{}' to {}.".format(host.name,
                                                   owner.id))
        log_user_event(author=processor,
                       user=host.owner,
                       message=message.to_json())

        message = deferred_gettext(
            u"Transferred Host '{}' from {}.".format(host.name,
                                                     host.owner.id))
        log_user_event(author=processor,
                       user=owner,
                       message=message.to_json())

        host.owner = owner

    if host.room != room:
        migrate_user_host(host, room, processor)

    if host.name != name:
        message = deferred_gettext(
            u"Changed name of host '{}' to '{}'.".format(host.name,
                                                         name))
        host.name = name

        log_user_event(author=processor,
                       user=owner,
                       message=message.to_json())


@with_transaction
def host_delete(host, processor):
    message = deferred_gettext("Deleted host '{}'.".format(host.name))
    log_user_event(author=processor,
                   user=host.owner,
                   message=message.to_json())

    session.delete(host)\


@with_transaction
def interface_create(host, mac, ips, processor):
    interface = Interface(host=host,
                          mac=mac)

    session.add(interface)

    subnets = get_subnets_for_room(interface.host.room)

    if ips is None:
        ip, _ = get_free_ip(subnets)
        ips = {ip}

    # IP added
    for ip in ips:
        subnet = next(
            iter([subnet for subnet in subnets if (ip in subnet.address)]),
            None)

        if subnet is not None:
            session.add(IP(interface=interface, address=ip,
                           subnet=subnet))

    message = deferred_gettext(u"Created interface ({}, {}) for host '{}'."
                               .format(interface.mac,
                                       ', '.join(str(ip.address) for ip in
                                                 interface.ips),
                                       interface.host.name))
    log_user_event(author=processor,
                   user=host.owner,
                   message=message.to_json())

    return interface


@with_transaction
def interface_edit(interface, host, mac, ips, processor):
    message = u"Edited interface ({}, {}) of host '{}'." \
        .format(interface.mac,
                ', '.join(str(ip.address) for ip in
                          interface.ips),
                interface.host.name)

    if interface.host != host:
        interface.host = host
        message += " New host: '{}'.".format(interface.host.name)

    if interface.mac != mac:
        interface.mac = mac
        message += " New MAC: {}.".format(interface.mac)

    ips_changed = False

    current_ips = list(ip.address for ip in interface.ips)
    subnets = get_subnets_for_room(interface.host.room)

    # IP removed
    for ip in current_ips:
        if ip not in ips:
            session.delete(IP.q.filter_by(address=ip).first())
            ips_changed = True

    # IP added
    for ip in ips:
        if ip not in current_ips:
            subnet = next(
                iter([subnet for subnet in subnets if (ip in subnet.address)]),
                None)

            if subnet is not None:
                session.add(IP(interface=interface, address=ip,
                                       subnet=subnet))
                ips_changed = True

    session.refresh(interface)

    if ips_changed:
        message += " New IPs: {}.".format(', '.join(str(ip.address) for ip in
                                                    interface.ips))

    log_user_event(author=processor,
                   user=interface.host.owner,
                   message=deferred_gettext(message).to_json())


@with_transaction
def interface_delete(interface, processor):
    message = deferred_gettext(u"Deleted interface {} of host {}."
                               .format(interface.mac, interface.host.name))
    log_user_event(author=processor,
                   user=interface.host.owner,
                   message=message.to_json())

    session.delete(interface)