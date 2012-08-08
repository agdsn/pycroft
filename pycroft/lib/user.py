# -*- coding: utf-8 -*-
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
from pycroft.model.hosts import Host, NetDevice
from pycroft.model.logging import UserLogEntry
from pycroft.model.session import session
from pycroft.model.user import User


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


def move(user, dormitory, level, room_number):
    oldRoom = user.room
    newRoom = Room.q.filter_by(number=room_number,
        level=level,
        dormitory_id=dormitory.id).one()
    user.room = newRoom
    session.add(user)

    newUserLogEntry = UserLogEntry(author_id=current_user.id,
        message=u"umgezogen von %s nach %s"%(oldRoom, newRoom),
        timestamp=datetime.now(), user_id=user.id)
    session.add(newUserLogEntry)

    session.commit()

    return user


def edit_name(user, name):
    if len(name):
        user.name = name

    session.add(user)
    session.commit()

    return user
