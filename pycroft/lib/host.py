# -*- coding: utf-8 -*-
# Copyright (c) 2014 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
import datetime
from pycroft.model.logging import UserLogEntry
from pycroft.model import session
from pycroft.model.session import with_transaction


@with_transaction
def change_mac(net_device, mac, processor):
    """
    This method will change the mac address of the given net device to the new
    mac address.

    :param net_device: the net device which should become a new mac address.
    :param mac: the new mac address.
    :param processor: the user who initiated the mac address change.
    :return: the changed net device with the new mac address.
    """
    net_device.mac = mac

    change_mac_log_entry = UserLogEntry(author_id=processor.id,
        message=u"Die Mac-Adresse in {} geändert.".format(mac),
        timestamp=datetime.datetime.utcnow(), user_id=net_device.host.user.id)

    session.session.add(change_mac_log_entry)
    return net_device
