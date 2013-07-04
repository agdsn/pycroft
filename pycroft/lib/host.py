# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

import datetime
from pycroft.model.logging import UserLogEntry
from pycroft.model import session
from pycroft.model.host import UserHost, ServerHost, Switch, UserNetDevice, \
    ServerNetDevice, SwitchNetDevice, Ip
from pycroft.lib.all import with_transaction


@with_transaction
def change_mac(net_device, mac, processor):
    """
    This method will change the mac address of the given netdevice to the new
    mac address.

    :param net_device: the netdevice which should become a new mac address.
    :param mac: the new mac address.
    :param processor: the user who initiated the mac address change.
    :return: the changed netdevice with the new mac address.
    """
    net_device.mac = mac

    change_mac_log_entry = UserLogEntry(author_id=processor.id,
        message=u"Die Mac-Adresse in %s geändert." % mac,
        timestamp=datetime.datetime.now(), user_id=net_device.host.user.id)

    session.session.add(change_mac_log_entry)
    return net_device


@with_transaction
def create_user_host(user, room):
    """
    This method will create a new UerHost.


    :param user: the user
    :param room: the room
    :return: the newly created UserHost.
    """
    user_host = UserHost(user=user, room=room)

    session.session.add(user_host)
    return user_host


@with_transaction
def delete_user_host(user_host_id):
    """
    This method will remove the UserHost for the given id.

    :param user_host_id: the id of the UserHost, which should be removed.
    :return: the removed UserHost.
    """
    del_user_host = UserHost.q.get(user_host_id)

    if del_user_host is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_user_host)
    return del_user_host


@with_transaction
def create_server_host(user, room):
    """
    This method will create a new ServerHost.

    :param user: the user
    :param room: the room
    :return: the newly created ServerHost.
    """
    server_host = ServerHost(user=user, room=room)
    session.session.add(server_host)
    return server_host


@with_transaction
def delete_server_host(server_host_id):
    """
    This method will remove a ServerHost for the given id.

    :param server_host_id: the id of the ServerHost which should be removed.
    :return: the removed ServerHost.
    """
    del_server_host = ServerHost.q.get(server_host_id)
    if del_server_host is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_server_host)
    return del_server_host


@with_transaction
def create_switch(user, room, name, management_ip):
    """
    This method will create a new switch.

    :param user: the id of the user
    :param room: the id of the room
    :param name: the name of the switch
    :param management_ip: the management ip which is used to access the switch
    :return: the newly created switch.
    """
    switch = Switch(user=user, room=room, name=name,
                    management_ip=management_ip)
    session.session.add(switch)
    return switch


@with_transaction
def delete_switch(switch_id):
    """
    This method will remove the switch for the given id.

    :param switch_id: the id of the switch which should be removed.
    :return: the removed switch.
    """
    del_switch = Switch.q.get(switch_id)
    if del_switch is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_switch)
    return del_switch


@with_transaction
def create_user_net_device(mac, host):
    """
    This method will create a new UserNetDevice.

    :param mac: the mac of the device
    :param host: the host
    :return: the newly created UserNetDevice.
    """
    user_net_device = UserNetDevice(mac=mac, host=host)
    session.session.add(user_net_device)
    return user_net_device


@with_transaction
def delete_user_net_device(user_net_device_id):
    """
    This method will remove the UserNetDevice for the given id.

    :param user_net_device_id: the id of the UserNetDevice which should be
                               deleted.
    :return: the removed UserNetDevice.
    """
    del_user_net_device = UserNetDevice.q.get(user_net_device_id)
    if del_user_net_device is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_user_net_device)
    return del_user_net_device


@with_transaction
def create_server_net_device(mac, host, switch_port):
    """
    This method will create a new ServerNetDevice.


    :param mac: the mac of the net device
    :param host: the host
    :param switch_port: the switch_port
    :return: the newly created ServerNetDevice.
    """
    server_net_device = ServerNetDevice(mac=mac, host=host,
                                        switch_port=switch_port)
    session.session.add(server_net_device)
    return server_net_device


@with_transaction
def delete_server_net_device(server_net_device_id):
    """
    This method will the ServerNetDevice for the given id.

    :param server_net_device_id: the id of the ServerNetDevice which should be
                                 removed.
    :return: the removed ServerNetDevice.
    """
    del_server_net_device = ServerNetDevice.q.get(server_net_device_id)
    if del_server_net_device is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_server_net_device)
    return del_server_net_device


@with_transaction
def create_switch_net_device(mac, host):
    """
    This method will create a new SwitchNetDevice.

    :param mac: the mac of the device
    :param host: the id of the host
    :return: the newly created SwitchNetDevice.
    """
    switch_net_device = SwitchNetDevice(mac=mac, host=host)
    session.session.add(switch_net_device)
    return switch_net_device


@with_transaction
def delete_switch_net_device(switch_net_device_id):
    """
    This method will remove the SwitchNetDevice for the given id.

    :param switch_net_device_id: the id of the SwitchNetDevice which should be
                                 deleted.
    :return: the removed SwitchNetDevice.
    """
    del_switch_net_device = SwitchNetDevice.q.get(switch_net_device_id)
    if del_switch_net_device is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_switch_net_device)
    return del_switch_net_device


@with_transaction
def create_ip(address, net_device, subnet):
    """
    This method will create a new Ip.

    :param address: the address which is represented by this object.
    :param net_device: the net_device.
    :param subnet: the subnet the ip is part of.
    :return: the newly created Ip.
    """
    ip = Ip(address=address, net_device=net_device, subnet=subnet)
    session.session.add(ip)
    return ip


@with_transaction
def delete_ip(ip_id):
    """
    This method will remove the Ip for the given id.

    :param ip_id: the id of the Ip which should be removed.
    :return: the removed Ip.
    """
    del_ip = Ip.q.get(ip_id)
    if del_ip is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_ip)
    return del_ip