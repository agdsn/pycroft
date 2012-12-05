# Copyright (c) 2012 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from pycroft.model import session
from pycroft.model.ports import SwitchPort

def create_switch_port(*args, **kwargs):
    """
    This method will create a new switch port.

    :param args: the positionals which will be passed to the constructor.
    :param kwargs: the keyword arguments which will be passed to the constructor.
    :return: the newly created switch port.
    """
    port = SwitchPort(*args, **kwargs)
    session.session.add(port)
    session.session.commit()

    return port
