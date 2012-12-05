# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

import datetime
from pycroft.model.logging import UserLogEntry
from pycroft.model import session

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
    session.session.commit()

    return net_device
