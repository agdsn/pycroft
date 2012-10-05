# -*- coding: utf-8 -*-
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
from pycroft.model import session
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
    session.session.add(new_user)

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

    session.session.add(new_host)
    session.session.add(new_net_device)
    session.session.add(new_ip)

    #TODO: add user to initial groups (create those memberships)

    #TODO: create financial account for user with negative balance

    #TODO: add membership that allows negative account balance for one month

    session.session.commit()

    return new_user

#TODO ensure serializability
def move(user, dormitory, level, room_number, processing_user):
    # change the room of the user

    def get_free_patchport(patch_ports):
        free_patch_ports = []
        for patch_port in patch_ports:
            if patch_port.net_device == None:
                free_patch_ports.append(patch_port)
        assert len(free_patch_ports) > 0
        return free_patch_ports[0]

    old_room = user.room
    new_room = Room.q.filter_by(number=room_number,
        level=level,
        dormitory_id=dormitory.id).one()

    assert old_room is not new_room, "A User is only allowed to move in a different room!"

    user.room = new_room
    session.session.add(user)

    moving_user_log_entry = UserLogEntry(author_id=processing_user.id,
        message=u"umgezogen von %s nach %s" % (old_room.dormitory.short_name, new_room),
        timestamp=datetime.now(), user_id=user.id)
    session.session.add(moving_user_log_entry)


    # TODO let choose which hosts should move in the same room, change only their net_devices
    net_device_qry = session.session.query(
        NetDevice
    ).join(
        NetDevice.host
    ).filter(
        Host.user_id == user.id
    )

    assert net_device_qry.count() == 1, u"You can not move users with %d network devices!" % net_device_qry.count()

    # assign a new IP to each net_device
    net_dev = net_device_qry.one()
    if old_room.dormitory_id != new_room.dormitory_id:
    #   for net_device in net_devices:
    #        for ip_addr in net_device.ips:
        assert len(net_dev.ips) == 1, u"A user should only have one ip!"
        ip_addr = net_dev.ips[0]
        old_ip = ip_addr.address
        new_address = host_helper.get_free_ip(dormitory.get_subnets())
        new_subnet = host_helper.select_subnet_for_ip(new_address,
                                            dormitory.get_subnets())

        ip_addr.change_ip(new_address, new_subnet)

        ip_change_log_entry = UserLogEntry(author_id=processing_user.id,
            message=u"IPv4 von %s auf %s geändert" % (
            old_ip, new_address),
            timestamp=datetime.now(), user_id=user.id)
        session.session.add(ip_change_log_entry)

    #TODO set new PatchPort for each NetDevice in each Host that moves to the new room
    #moves the host in the new room and assign the belonging net_device to the new patch_port
    user.hosts[0].room = new_room
    net_dev.patch_port = get_free_patchport(new_room.patch_ports)

    session.session.commit()
    return user


def edit_name(user, name):
    oldName = user.name
    if len(name):
        user.name = name
    session.session.add(user)

    newUserLogEntry = UserLogEntry(author_id=current_user.id,
        message=u"Nutzer %s umbenannt in %s" % (oldName, name),
        timestamp=datetime.now(), user_id=user.id)
    session.session.add(newUserLogEntry)

    session.session.commit()

    return user


#ToDo: Usecases überprüfen: standardmäßig nicht False?
def has_exceeded_traffic(user):
    result = session.session.query(User.id, (func.max(TrafficGroup.traffic_limit) * 1.10) < func.sum(TrafficVolume.size).label("has_exceeded_traffic")).join(User.active_traffic_groups).join(User.hosts).join(Host.ips).join(Ip.traffic_volumes).filter(User.id == user.id).group_by(User.id).first()
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
                if has_positive_balance(user):
                    return True
                else:
                    return False
    else:
        return False
