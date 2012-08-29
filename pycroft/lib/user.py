# -*- coding: utf-8 -*-
# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.lib.user
~~~~~~~~~~~~~~

This module contains.

:copyright: (c) 2012 by AG DSN.
"""

from datetime import datetime
from flask.ext.login import current_user
from pycroft.helpers import user_helper, host_helper
from pycroft.model.dormitory import Dormitory, Room, Subnet, VLan
from pycroft.model.hosts import Host, NetDevice, Ip
from pycroft.model.logging import UserLogEntry
from pycroft.model.session import session
from pycroft.model.user import User


def moves_in(name, login, dormitory, level, room_number, host_name, mac):
    subnets = dormitory.get_subnets()
    ip_address = host_helper.get_free_ip(subnets)
    subnet = host_helper.select_subnet_for_ip(ip_address, subnets)

    if not host_name:
        host_name = host_helper.generate_hostname(ip_address)

    room = Room.q.filter_by(number=room_number,
        level=level, dormitory_id=dormitory.id).one()

    #ToDo: Which port to choose if room has more than one?
    # --> The one that is connected to a switch!
    patch_port = room.patch_ports[0]

    new_user = User(login=login,
        name=name,
        room=room,
        registration_date=datetime.now())
    plain_password = user_helper.generatePassword(12)

    #TODO: DEBUG remove in productive!!!
    print u"new password: " + plain_password
    new_user.set_password(plain_password)
    session.add(new_user)

    new_host = Host(hostname=host_name,
        user=new_user,
        room=room)
    session.add(new_host)

    new_net_device = NetDevice(mac=mac, host=new_host, patch_port=patch_port)
    new_ip = Ip(net_device=new_net_device, address=ip_address, subnet=subnet)

    session.add(new_net_device)
    session.add(new_ip)

    session.commit()

    return new_user


def move(user, dormitory, level, room_number):
    oldRoom = user.room
    newRoom = Room.q.filter_by(number=room_number,
        level=level,
        dormitory_id=dormitory.id).one()
    user.room = newRoom
    session.add(user)

    newUserLogEntry = UserLogEntry(author_id=current_user.id,
        message=u"umgezogen von %s nach %s" % (oldRoom, newRoom),
        timestamp=datetime.now(), user_id=user.id)
    session.add(newUserLogEntry)

    if oldRoom.dormitory_id != newRoom.dormitory_id:
        #TODO let choose which hosts should move in the same room
        netdevices = session.query(
            NetDevice
        ).join(
            NetDevice.host
        ).filter(
            Host.user_id == user.id
        ).all()

        for netdevice in netdevices:
            #TODO set new patchport
            for ip_addr in netdevice.ips:
                old_ip = ip_addr.address
                new_address = host_helper.get_free_ip(dormitory.get_subnets())
                new_subnet = host_helper.select_subnet_for_ip(new_address,
                                                    dormitory.get_subnets())
            
                ip_addr.change_ip(new_address, new_subnet)
            
                newUserLogEntry = UserLogEntry(author_id=current_user.id,
                    message=u"IPv4 von %s auf %s geändert" % (
                    old_ip, new_address),
                    timestamp=datetime.now(), user_id=user.id)
                session.add(newUserLogEntry)

    session.commit()
    return user


def edit_name(user, name):
    oldName = user.name
    if len(name):
        user.name = name
    session.add(user)

    newUserLogEntry = UserLogEntry(author_id=current_user.id,
        message=u"Nutzer %s umbenannt in %s" % (oldName, name),
        timestamp=datetime.now(), user_id=user.id)
    session.add(newUserLogEntry)

    session.commit()

    return user


#ToDo: Funktion zum Überprüfen des Trafficlimits
def has_exceeded_traffic(user):
    return False


#ToDo: Funktion zur Abfrage dr Kontobilanz
def has_positive_balance(user):
    return True

def has_internet(user):
    if user.has_property("internet"):
        if user.has_property("no_internet"):
            return False
        else:
            if has_exceeded_traffic(user):
                return False
            else:
                if has_positive_bilance(user):
                    return True
                else:
                    return False
    else:
        return False
