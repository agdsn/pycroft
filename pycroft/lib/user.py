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
from pycroft.helpers import user_helper, host_helper
from pycroft.model.session import session
from pycroft.model.dormitory import Dormitory, Room, Subnet, VLan
from pycroft.model.user import User
from pycroft.model.hosts import Host, NetDevice

def moves_in(name, login, dormitory, level, room_number, host_name, mac):
    #ToDo: Ugly, but ... Someone can convert this is
    #      a proper property of Dormitory
    #ToDo: Also possibly slow and untested
    subnets = session.query(
        Subnet
    ).join(
        Subnet.vlans
    ).join(
        VLan.dormitories
    ).filter(
        Dormitory.id == dormitory.id
    ).all()

    ip_address = host_helper.getFreeIP(subnets)

    if not host_name:
        host_name = host_helper.generateHostname(ip_address)

    room = Room.q.filter_by(number=room_number,
        level=level, dormitory_id=dormitory.id).one()

    #ToDo: Which port to choose if room has more than one?
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

    new_net_device = NetDevice(ipv4=ip_address,
        mac=mac,
        host=new_host,
        patch_port=patch_port)
    session.add(new_net_device)
    session.commit()

    return new_user

def edit_user(user, name, dormitory, level, room_number):
    room = Room.q.filter_by(number=room_number,
        level=level, dormitory_id=dormitory.id).one()

    if len(name):
        user.name = name
    if room is not None:
        user.room = room

    session.add(user)
    session.commit()

    return user
