# -*- coding: utf-8 -*-
__author__ = 'Florian Österreich'

import datetime
from pycroft.model.logging import UserLogEntry
from pycroft.model import session

def change_mac(net_device, mac, processor):
    net_device.mac = mac

    change_mac_log_entry = UserLogEntry(author_id=processor.id,
        message=u"Die Mac-Adresse in %s geändert." % mac,
        timestamp=datetime.datetime.now(), user_id=net_device.host.user.id)

    session.session.add(net_device)
    session.session.add(change_mac_log_entry)

    session.session.commit()

    return net_device

