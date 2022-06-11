import ipaddr
from ipaddr import IPAddress

from pycroft.helpers.i18n import deferred_gettext
from pycroft.lib.exc import PycroftLibException
from pycroft.lib.logging import log_room_event
from pycroft.model.facilities import Room
from pycroft.model.host import SwitchPort, Host, Switch
from pycroft.model.port import PatchPort
from pycroft.model.session import with_transaction, session
from pycroft.model.user import User


class PatchPortAlreadyPatchedException(PycroftLibException):
    pass


class PatchPortAlreadyExistsException(PycroftLibException):
    pass


@with_transaction
def create_patch_port(name, room, switch_room, processor):
    # This check can be removed as soon as the unique constraint exists
    if PatchPort.q.filter_by(name=name, switch_room=switch_room).first():
        raise PatchPortAlreadyExistsException()

    patch_port = PatchPort(name=name, room=room, switch_room=switch_room)
    session.add(patch_port)

    message = (
        deferred_gettext("Created patch-port {} to {}.")
        .format(patch_port.name, room.short_name)
        .to_json()
    )
    log_room_event(message, processor, switch_room)
    return patch_port


@with_transaction
def edit_patch_port(patch_port, name, room, processor):
    if patch_port.name != name:
        # This check can be removed as soon as the unique constraint exists
        if PatchPort.q.filter_by(name=name, switch_room=patch_port.switch_room).first():
            raise PatchPortAlreadyExistsException()

        message = deferred_gettext("Changed name of patch-port {patch_port_name} to {name}.")\
            .format(patch_port_name=patch_port.name, name=name)
        log_room_event(message.to_json(), processor, patch_port.switch_room)

        patch_port.name = name

    if patch_port.room != room:
        message = deferred_gettext("Changed room of patch-port {pp}"
                                   " from {old_room} to {new_room}.")\
            .format(pp=patch_port.name, old_room=patch_port.room.short_name,
                    new_room=room.short_name)
        log_room_event(message.to_json(), processor, patch_port.switch_room)

        patch_port.room = room


@with_transaction
def delete_patch_port(patch_port, processor):
    message = deferred_gettext("Deleted patch-port {}.").format(patch_port.name)
    log_room_event(message.to_json(), processor, patch_port.switch_room)

    session.delete(patch_port)


@with_transaction
def patch_switch_port_to_patch_port(switch_port, patch_port, processor):
    if patch_port.switch_port:
        raise PatchPortAlreadyPatchedException()

    message = (
        deferred_gettext("Added patch from {host}/{switch_port} to {patch_port}.")
        .format(
            host=switch_port.switch.host.name,
            switch_port=switch_port.name,
            patch_port=patch_port.name,
        )
    )
    log_room_event(message,
                   processor, switch_port.switch.host.room)

    patch_port.switch_port = switch_port


@with_transaction
def remove_patch_to_patch_port(patch_port, processor):
    if not patch_port.switch_port:
        raise Exception("Patch-port is not patched to a switch-port.")

    switch_port = patch_port.switch_port

    message = (
        deferred_gettext("Removed patch from {host}/{switch_port} to {patch_port}.")
        .format(
            host=switch_port.switch.host.name,
            switch_port=switch_port.name,
            patch_port=patch_port.name,
        )
    )
    log_room_event(message,
                   processor, switch_port.switch.host.room)

    patch_port.switch_port = None


@with_transaction
def create_switch_port(switch, name, default_vlans, processor):
    switch_port = SwitchPort(name=name, switch=switch, default_vlans=default_vlans)
    session.add(switch_port)

    default_vlans_str = ', '.join(str(vlan.vid) for vlan in switch_port.default_vlans)
    message = deferred_gettext("Created switch-port {} on {} with default VLANs {}.")\
        .format(switch_port.name, switch_port.switch.host.name, default_vlans_str)
    log_room_event(message.to_json(), processor, switch_port.switch.host.room)

    return switch_port


@with_transaction
def edit_switch_port(switch_port, name,  default_vlans, processor):
    if switch_port.name != name:
        message = deferred_gettext("Changed name of switch-port {} to {}.")\
            .format(switch_port.name, name)
        log_room_event(message.to_json(), processor, switch_port.switch.host.room)

        switch_port.name = name

    if switch_port.default_vlans != default_vlans:
        switch_port.default_vlans = default_vlans

        new_default_vlans_str = ', '.join(str(vlan.vid) for vlan in switch_port.default_vlans)
        message = deferred_gettext("Changed default VLANs of switch-port {} to {}.")\
            .format(switch_port.name, new_default_vlans_str)
        log_room_event(message.to_json(), processor, switch_port.switch.host.room)


@with_transaction
def delete_switch_port(switch_port, processor):
    message = deferred_gettext("Deleted switch-port {port} on {host}.")\
        .format(port=switch_port.name, host=switch_port.switch.host.name)
    log_room_event(message.to_json(), processor, switch_port.switch.host.room)

    session.delete(switch_port)


@with_transaction
def edit_switch(switch, name, management_ip, room, processor):
    if switch.host.name != name:
        message = deferred_gettext("Changed switch name from '{old}' to '{new}'.")\
            .format(old=switch.host.name, new=name)
        log_room_event(message.to_json(), processor, switch.host.room)

        switch.host.name = name

    if switch.host.room != room:
        message = deferred_gettext("Moved switch '{}' from {} to {}.")\
            .format(switch.host.name, switch.host.room, room)
        log_room_event(message.to_json(), processor, switch.host.room)

        switch.host.room = room

    if switch.management_ip != IPAddress(management_ip):
        message = deferred_gettext("Changed management IP of switch '{}' from {} to {}.")\
            .format(switch.host.name, switch.management_ip, management_ip)
        log_room_event(message.to_json(), processor, switch.host.room)

        switch.management_ip = management_ip


@with_transaction
def create_switch(
    name: str, management_ip: ipaddr.IPv4Address, room: Room, processor: User
):
    switch = Switch(
        management_ip=management_ip, host=Host(room=room, owner=User.get(0), name=name)
    )
    session.add(switch)

    message = deferred_gettext("Created switch '{}' with management IP {}.")\
        .format(switch.host.name, switch.management_ip)
    log_room_event(message.to_json(),
                   processor, switch.host.room)

    return switch


@with_transaction
def delete_switch(switch, processor):
    message = deferred_gettext("Deleted switch {}.").format(switch.host.name)
    log_room_event(message, processor, switch.host.room)

    session.delete(switch)
    session.delete(switch.host)
