# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

import datetime
from pycroft.model.logging import UserLogEntry
from pycroft.model import session

from pycroft.model.host import UserHost, ServerHost, Switch, UserNetDevice, \
    ServerNetDevice, SwitchNetDevice, Ip


def change_mac(net_device, mac, processor, commit=True):
    """
    This method will change the mac address of the given netdevice to the new
    mac address.

    :param net_device: the netdevice which should become a new mac address.
    :param mac: the new mac address.
    :param processor: the user who initiated the mac address change.
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the changed netdevice with the new mac address.
    """
    net_device.mac = mac

    change_mac_log_entry = UserLogEntry(author_id=processor.id,
        message=u"Die Mac-Adresse in %s geändert." % mac,
        timestamp=datetime.datetime.now(), user_id=net_device.host.user.id)

    session.session.add(change_mac_log_entry)
    if commit:
        session.session.commit()

    return net_device


def create_user_host(user_id, room_id, commit=True):
    """
    This method will create a new UerHost.


    :param user_id: the id of the user
    :param room_id: the id of the room
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the newly created UserHost.
    """
    user_host = UserHost(user_id=user_id, room_id=room_id)

    session.session.add(user_host)
    if commit:
        session.session.commit()

    return user_host


def delete_user_host(user_host_id, commit=True):
    """
    This method will remove the UserHost for the given id.

    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :param user_host_id: the id of the UserHost, which should be removed.
    :return: the removed UserHost.
    """
    del_user_host = UserHost.q.get(user_host_id)

    if del_user_host is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_user_host)
    if commit:
        session.session.commit()

    return del_user_host


def create_server_host(user_id, room_id, commit=True):
    """
    This method will create a new ServerHost.

    :param user_id: the id of the user
    :param room_id: the id of the room
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the newly created ServerHost.
    """
    server_host = ServerHost(user_id=user_id, room_id=room_id)
    session.session.add(server_host)
    if commit:
        session.session.commit()

    return server_host


def delete_server_host(server_host_id, commit=True):
    """
    This method will remove a ServerHost for the given id.

    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :param server_host_id: the id of the ServerHost which should be removed.
    :return: the removed ServerHost.
    """
    del_server_host = ServerHost.q.get(server_host_id)
    if del_server_host is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_server_host)
    if commit:
        session.session.commit()

    return del_server_host


def create_switch(user_id, room_id, name, management_ip, commit=True):
    """
    This method will create a new switch.

    :param user_id: the id of the user
    :param room_id: the id of the room
    :param name: the name of the switch
    :param management_ip: the management ip which is used to access the switch
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the newly created switch.
    """
    switch = Switch(user_id=user_id, room_id=room_id, name=name,
                    management_ip=management_ip)
    session.session.add(switch)
    if commit:
        session.session.commit()

    return switch


def delete_switch(switch_id, commit=True):
    """
    This method will remove the switch for the given id.

    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :param switch_id: the id of the switch which should be removed.
    :return: the removed switch.
    """
    del_switch = Switch.q.get(switch_id)
    if del_switch is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_switch)
    if commit:
        session.session.commit()

    return del_switch


def create_user_net_device(mac, host_id, commit=True):
    """
    This method will create a new UserNetDevice.

    :param mac: the mac of the device
    :param host_id: the id of the host
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the newly created UserNetDevice.
    """
    user_net_device = UserNetDevice(mac=mac, host_id=host_id)
    session.session.add(user_net_device)
    if commit:
        session.session.commit()

    return user_net_device


def delete_user_net_device(user_net_device_id, commit=True):
    """
    This method will remove the UserNetDevice for the given id.

    :param user_net_device_id: the id of the UserNetDevice which should be
                               deleted.
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the removed UserNetDevice.
    """
    del_user_net_device = UserNetDevice.q.get(user_net_device_id)
    if del_user_net_device is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_user_net_device)
    if commit:
        session.session.commit()

    return del_user_net_device


def create_server_net_device(mac, host_id, switch_port_id, commit=True):
    """
    This method will create a new ServerNetDevice.


    :param mac: the mac of the net device
    :param host_id: the id of the host
    :param switch_port_id: the id of the switch_port
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the newly created ServerNetDevice.
    """
    server_net_device = ServerNetDevice(mac=mac, host_id=host_id,
                                        switch_port_id=switch_port_id)
    session.session.add(server_net_device)
    if commit:
        session.session.commit()

    return server_net_device


def delete_server_net_device(server_net_device_id, commit=True):
    """
    This method will the ServerNetDevice for the given id.

    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :param server_net_device_id: the id of the ServerNetDevice which should be
                                 removed.
    :return: the removed ServerNetDevice.
    """
    del_server_net_device = ServerNetDevice.q.get(server_net_device_id)
    if del_server_net_device is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_server_net_device)
    if commit:
        session.session.commit()

    return del_server_net_device


def create_switch_net_device(mac, host_id, commit=True):
    """
    This method will create a new SwitchNetDevice.

    :param mac: the mac of the device
    :param host_id: the id of the host
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the newly created SwitchNetDevice.
    """
    switch_net_device = SwitchNetDevice(mac=mac, host_id=host_id)
    session.session.add(switch_net_device)
    if commit:
        session.session.commit()

    return switch_net_device


def delete_switch_net_device(switch_net_device_id, commit=True):
    """
    This method will remove the SwitchNetDevice for the given id.

    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :param switch_net_device_id: the id of the SwitchNetDevice which should be
                                 deleted.
    :return: the removed SwitchNetDevice.
    """
    del_switch_net_device = SwitchNetDevice.q.get(switch_net_device_id)
    if del_switch_net_device is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_switch_net_device)
    if commit:
        session.session.commit()

    return del_switch_net_device


def create_ip(address, net_device_id, subnet_id, commit=True):
    """
    This method will create a new Ip.

    :param address: the address which is represented by this object.
    :param net_device_id: the id of the net_device.
    :param subnet_id: the id of the subnet the ip is part of.
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the newly created Ip.
    """
    ip = Ip(address=address, net_device_id=net_device_id, subnet_id=subnet_id)
    session.session.add(ip)
    if commit:
        session.session.commit()

    return ip


def delete_ip(ip_id, commit=True):
    """
    This method will remove the Ip for the given id.

    :param ip_id: the id of the Ip which should be removed.
    :param commit: flag which indicates whether the session should be
                   commited or not. Default: True
    :return: the removed Ip.
    """
    del_ip = Ip.q.get(ip_id)
    if del_ip is None:
        raise ValueError("The given id is wrong!")

    session.session.delete(del_ip)
    if commit:
        session.session.commit()

    return del_ip