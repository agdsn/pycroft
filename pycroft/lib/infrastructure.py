from pycroft.model import session
from pycroft.model.port import SwitchPort, DestinationPort, PatchPort, \
    PhonePort, Port

def _create_port(type, commit=True, *args, **kwargs):
    """
    This method will create a new port.

    :param type: the type of the port.
    :param commit: flag which indicates whether the session should be
                   committed or not. Default: True
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
    if commit:
        session.session.commit()

    return port


def create_patch_port(name, room, destination_port=None, commit=True):
    """
    This method will create a new PatchPort.

    :param name: the name of the port
    :param room: the room
    :param destination_port: the port this port is connected to
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created PatchPort.
    """
    return _create_port("patch_port", name=name, room=room,
                        destination_port=destination_port, commit=commit)


def create_phone_port(name, commit=True):
    """
    This method will create a new PhonePort.

    :param name: the name of the port
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created PhonePort.
    """
    return _create_port("phone_port", name=name, commit=commit)


def create_switch_port(name, switch, commit=True):
    """
    This method will create a new SwitchPort.

    :param name: the name of the port
    :param switch: the switch which has the port
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
    :return: the newly created SwitchPort.
    """
    return _create_port("switch_port", name=name, switch=switch,
                        commit=commit)


def delete_port(port_id, commit=True):
    """
    This method will remove the Port for the given id.

    :param port_id: the id of the Port which should be removed.
    :param commit: flag which indicates whether the session should be committed
                   or not. Default: True
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
    if commit:
        session.session.commit()

    return del_port