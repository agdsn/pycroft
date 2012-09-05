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
from sqlalchemy.sql.expression import func
from pycroft.helpers import user_helper, host_helper
from pycroft.model.accounting import TrafficVolume
from pycroft.model.dormitory import Dormitory, Room, Subnet, VLan
from pycroft.model.hosts import Host, NetDevice, Ip
from pycroft.model.logging import UserLogEntry
from pycroft.model.properties import TrafficGroup
from pycroft.model.session import session
from pycroft.model.user import User


def moves_in(name, login, dormitory, level, room_number, host_name, mac):

    room = Room.q.filter_by(number=room_number,
        level=level, dormitory_id=dormitory.id).one()

    # create a new user
    new_user = User(login=login,
        name=name,
        room=room,
        registration_date=datetime.now())
    plain_password = user_helper.generatePassword(12)


    #TODO: print plain password on paper instead
    print u"new password: " + plain_password

    # set random initial password
    new_user.set_password(plain_password)
    session.add(new_user)

    # create one new host (including net_device) for the new user
    subnets = dormitory.get_subnets()
    ip_address = host_helper.get_free_ip(subnets)
    subnet = host_helper.select_subnet_for_ip(ip_address, subnets)
    #ToDo: Which port to choose if room has more than one?
    # --> The one that is connected to a switch!
    # ---> what if there are two or more ports in one room connected to the switch? (double bed room)
    patch_port = room.patch_ports[0]

    if not host_name:
        host_name = host_helper.generate_hostname(ip_address)

    new_host = Host(hostname=host_name,
        user=new_user,
        room=room)

    new_net_device = NetDevice(mac=mac, host=new_host, patch_port=patch_port)
    new_ip = Ip(net_device=new_net_device, address=ip_address, subnet=subnet)

    session.add(new_host)
    session.add(new_net_device)
    session.add(new_ip)

    #TODO: add user to initial groups (create those memberships)

    #TODO: create financial account for user with negative balance

    #TODO: add membership that allows negative account balance for one month

    session.commit()

    return new_user


def move(user, dormitory, level, room_number):
    # change the room of the user
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


    # TODO let choose which hosts should move in the same room, change only their net_devices
    net_devices = session.query(
        NetDevice
    ).join(
        NetDevice.host
    ).filter(
        Host.user_id == user.id
    ).all()

    # assign a new IP to each net_device
    if oldRoom.dormitory_id != newRoom.dormitory_id:
       for net_device in net_devices:
            for ip_addr in net_device.ips:
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

    #TODO set new PatchPort for each NetDevice in each Host that moves to the new room
    #for netdevice in netdevices:
    #    pass

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


#ToDo: Usecases überprüfen: standardmäßig nicht False?
def has_exceeded_traffic(user):
    result = session.query(User.id, (func.max(TrafficGroup.traffic_limit) * 1.10) < func.sum(TrafficVolume.size).label("has_exceeded_traffic")).join(User.active_traffic_groups).join(User.hosts).join(Host.ips).join(Ip.traffic_volumes).filter(User.id == user.id).group_by(User.id).first()
    if result is not None:
        return result.has_exceeded_traffic
    else: return False

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
