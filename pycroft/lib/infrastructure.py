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
