# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.host
~~~~~~~~~~~~~~~~
"""
import typing as t

import ipaddr

from pycroft.helpers.i18n import deferred_gettext
from pycroft.helpers.net import port_name_sort_key
from pycroft.lib.logging import log_user_event
from pycroft.lib.net import get_subnets_for_room, get_free_ip, delete_ip
from pycroft.lib.user import migrate_user_host
from pycroft.model.facilities import Room
from pycroft.model.host import Interface, IP, Host, SwitchPort
from pycroft.model.session import with_transaction, session
from pycroft.model.user import User


@with_transaction
def change_mac(interface: Interface, mac: str, processor: User) -> Interface:
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
    message = deferred_gettext("Changed MAC address from {} to {}.").format(
        old_mac, mac)
    if interface.host.owner:
        log_user_event(message.to_json(), processor, interface.host.owner)
    return interface


def generate_hostname(ip_address: ipaddr.IPv4Address) -> str:
    numeric_ip = int(ip_address)
    return "x{:02x}{:02x}{:02x}{:02x}".format(
        (numeric_ip >> 0x18) & 0xFF,
        (numeric_ip >> 0x10) & 0xFF,
        (numeric_ip >> 0x08) & 0xFF,
        (numeric_ip >> 0x00) & 0xFF,
    )


@with_transaction
def host_create(owner: User, room: Room, name: str, processor: User) -> Host:
    host = Host(name=name, owner_id=owner.id, room=room)

    session.add(host)

    message = (
        deferred_gettext("Created host '{name}' in {dorm} {level}-{room}.")
        .format(
            name=host.name,
            dorm=room.building.short_name,
            level=room.level,
            room=room.number,
        )
    )
    log_user_event(author=processor,
                   user=owner,
                   message=message.to_json())

    return host


@with_transaction
def host_edit(host: Host, owner: User, room: Room, name: str, processor: User) -> None:
    if host.name != name:
        message = deferred_gettext("Changed name of host '{}' to '{}'.").format(
            host.name, name
        )
        host.name = name

        log_user_event(author=processor,
                       user=owner,
                       message=message.to_json())

    if host.owner_id != owner.id:
        message = deferred_gettext("Transferred Host '{}' to {}.").format(
            host.name, owner.id
        )
        log_user_event(author=processor, user=host.owner, message=message.to_json())

        message = deferred_gettext("Transferred Host '{}' from {}.").format(
            host.name, host.owner.id
        )
        log_user_event(author=processor, user=owner, message=message.to_json())

        host.owner = owner

    if host.room != room:
        migrate_user_host(host, room, processor)


@with_transaction
def host_delete(host: Host, processor: User) -> None:
    message = deferred_gettext("Deleted host '{}'.").format(host.name)
    log_user_event(author=processor, user=host.owner, message=message.to_json())

    session.delete(host)


@with_transaction
def interface_create(
    host: Host,
    name: str,
    mac: str,
    ips: t.Iterable[ipaddr.IPv4Address] | None,
    processor: User,
) -> Interface:
    interface = Interface(host=host, mac=mac, name=name)

    session.add(interface)

    subnets = get_subnets_for_room(interface.host.room)

    if ips is None:
        # this happens in only one call
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

    message = deferred_gettext(
        "Created interface ({}, {}) with name '{}' for host '{}'."
    ).format(
        interface.mac,
        ", ".join(str(ip_.address) for ip_ in interface.ips),
        interface.name,
        interface.host.name,
    )
    log_user_event(author=processor, user=host.owner, message=message.to_json())

    return interface


@with_transaction
def interface_edit(
    interface: Interface,
    name: str,
    mac: str,
    ips: t.Iterable[ipaddr._BaseIP],
    processor: User,
) -> None:
    message = "Edited interface ({}, {}) of host '{}'.".format(
        interface.mac,
        ", ".join(str(ip.address) for ip in interface.ips),
        interface.host.name,
    )

    if interface.name != name:
        interface.name = name
        message += f" New name: '{interface.name}'."

    if interface.mac != mac:
        interface.mac = mac
        message += f" New MAC: {interface.mac}."

    ips_changed = False

    current_ips = list(ip.address for ip in interface.ips)
    subnets = get_subnets_for_room(interface.host.room)

    new_ips = set(current_ips)

    # IP removed
    for ip in current_ips:
        if ip not in ips:
            delete_ip(session, ip)
            ips_changed = True
            new_ips.remove(ip)

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
                new_ips.add(ipaddr.IPAddress(ip))

    if ips_changed:
        message += " New IPs: {}.".format(', '.join(str(ip) for ip in
                                                    new_ips))

    log_user_event(author=processor,
                   user=interface.host.owner,
                   message=deferred_gettext(message).to_json())


@with_transaction
def interface_delete(interface: Interface, processor: User) -> None:
    message = deferred_gettext("Deleted interface {} of host {}.").format(
        interface.mac, interface.host.name
    )
    log_user_event(
        author=processor, user=interface.host.owner, message=message.to_json()
    )

    session.delete(interface)


def sort_ports(ports: t.Iterable[SwitchPort]) -> list[SwitchPort]:
    def make_sort_key(port: SwitchPort) -> int:
        return port_name_sort_key(port.name)

    return sorted(ports, key=make_sort_key)
