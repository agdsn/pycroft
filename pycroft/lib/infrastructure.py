# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model import session
from pycroft.model.port import SwitchPort, DestinationPort, PatchPort, \
    PhonePort, Port

def _create_port(type, *args, **kwargs):
    """
    This method will create a new port.

    :param type: the type of the port.
    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created port.
    """
    type = str(type).lower()

    if type == "patch_port":
        port = PatchPort(*args, **kwargs)
    elif type == "phone_port":
        port = PhonePort(*args, **kwargs)
    elif type == "switch_port":
        port = SwitchPort(*args, **kwargs)
    else:
        raise ValueError("Unknown port type!")

    session.session.add(port)
    session.session.commit()

    return port


def create_patch_port(*args, **kwargs):
    """
    This method will create a new PatchPort.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created PatchPort.
    """
    return _create_port("patch_port", *args, **kwargs)


def create_phone_port(*args, **kwargs):
    """
    This method will create a new PhonePort.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created PhonePort.
    """
    return _create_port("phone_port", *args, **kwargs)


def create_switch_port(*args, **kwargs):
    """
    This method will create a new SwitchPort.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created SwitchPort.
    """
    return _create_port("switch_port", *args, **kwargs)


def delete_port(port_id):
    """
    This method will remove the Port for the given id.

    :param port_id: the id of the Port which should be removed.
    :return: the removed Port.
    """
    port = Port.q.get(port_id)
    if port is None:
        raise ValueError("The given id wrong!")

    if port.discriminator == "patch_port":
        del_port = PatchPort.q.get(port_id)
    elif port.discriminator == "phone_port":
        del_port = PhonePort.q.get(port_id)
    elif port.discriminator == "switch_port":
        del_port = SwitchPort.q.get(port_id)
    else:
        raise ValueError("Unknown port type!")

    session.session.delete(del_port)
    session.session.commit()

    return del_port
