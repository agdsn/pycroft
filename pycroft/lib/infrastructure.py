from ipaddr import IPAddress

from pycroft.lib.logging import log_room_event, log_event
from pycroft.model.host import SwitchPort, Host, Switch
from pycroft.model.port import PatchPort
from pycroft.model.session import with_transaction, session
from pycroft.model.user import User


class PatchPortAlreadyPatchedException(Exception):
    pass


class PatchPortAlreadyExistsException(Exception):
    pass


@with_transaction
def create_patch_port(name, room, switch_room, processor):
    # This check can be removed as soon as the unique constraint exists
    if PatchPort.q.filter_by(name=name, switch_room=switch_room).first():
        raise PatchPortAlreadyExistsException()

    patch_port = PatchPort(name=name, room=room, switch_room=switch_room)
    session.add(patch_port)

    log_room_event("Created patch-port {} to {}.".format(patch_port.name, room.short_name), processor, switch_room)

    return patch_port


@with_transaction
def edit_patch_port(patch_port, name, room, processor):
    if patch_port.name != name:
        # This check can be removed as soon as the unique constraint exists
        if PatchPort.q.filter_by(name=name, switch_room=patch_port.switch_room).first():
            raise PatchPortAlreadyExistsException()

        log_room_event("Changed name of patch-port {} to {}.".format(patch_port.name, name),
                       processor, patch_port.switch_room)

        patch_port.name = name

    if patch_port.room != room:
        log_room_event("Changed room of patch-port {} from {} to {}."
                       .format(patch_port.name, patch_port.room.short_name, room.short_name),
                       processor, patch_port.switch_room)

        patch_port.room = room


@with_transaction
def delete_patch_port(patch_port, processor):
    log_room_event("Deleted patch-port {}.".format(patch_port.name), processor, patch_port.switch_room)

    session.delete(patch_port)


@with_transaction
def patch_switch_port_to_patch_port(switch_port, patch_port, processor):
    if patch_port.switch_port:
        raise PatchPortAlreadyPatchedException()

    log_room_event("Added patch from {}/{} to {}.".format(switch_port.switch.host.name, switch_port.name, patch_port.name),
                   processor, switch_port.switch.host.room)

    patch_port.switch_port = switch_port


@with_transaction
def remove_patch_to_patch_port(patch_port, processor):
    if not patch_port.switch_port:
        raise Exception("Patch-port is not patched to a switch-port.")

    switch_port = patch_port.switch_port

    log_room_event("Removed patch from {}/{} to {}.".format(switch_port.switch.host.name, switch_port.name, patch_port.name),
                   processor, switch_port.switch.host.room)

    patch_port.switch_port = None


@with_transaction
def create_switch_port(switch, name, processor):
    switch_port = SwitchPort(name=name, switch=switch)
    session.add(switch_port)

    log_room_event("Created switch-port {} on {}.".format(switch_port.name, switch_port.switch.host.name), processor,
                   switch_port.switch.host.room)

    return switch_port


@with_transaction
def edit_switch_port(switch_port, name, processor):
    if switch_port.name != name:
        log_room_event("Changed name of switch-port {} to {}." .format(switch_port.name,name),
                       processor, switch_port.switch.host.room)

        switch_port.name = name


@with_transaction
def delete_switch_port(switch_port, processor):
    log_room_event("Deleted switch-port {} on {}.".format(switch_port.name, switch_port.switch.host.name), processor, switch_port.switch.host.room)

    session.delete(switch_port)


@with_transaction
def edit_switch(switch, name, management_ip, room, processor):
    if switch.host.name != name:
        log_room_event("Changed name of '{}' to '{}'.".format(switch.host.name, name), processor, switch.host.room)

        switch.host.name = name

    if switch.host.room != room:
        log_room_event("Moved switch '{}' from {} to {}.".format(switch.host.name, switch.host.room, room), processor, switch.host.room)

        switch.host.room = room

    if switch.management_ip != IPAddress(management_ip):
        log_room_event("Changed management IP of switch '{}' from {} to {}."
                       .format(switch.host.name, switch.management_ip, management_ip), processor, switch.host.room)

        switch.management_ip = management_ip


@with_transaction
def create_switch(name, management_ip, room, processor):
    switch = Switch(management_ip=management_ip, host=Host(room=room, owner=User.q.get(0), name=name))

    session.add(switch)

    log_room_event("Created switch '{}' with management IP {}.".format(switch.host.name, switch.management_ip),
                   processor, switch.host.room)

    return switch


@with_transaction
def delete_switch(switch, processor):
    log_room_event("Deleted switch {}.".format(switch.host.name), processor, switch.host.room)

    session.delete(switch)
