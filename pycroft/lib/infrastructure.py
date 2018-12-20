from pycroft.lib.logging import log_room_event, log_event
from pycroft.model.host import SwitchPort, Host, Switch
from pycroft.model.port import PatchPort
from pycroft.model.session import with_transaction, session
from pycroft.model.user import User


@with_transaction
def edit_port_relation(switchport, patchport, switchport_name, patchport_name, room, processor):
    if patchport.room != room:
        log_room_event("Changed room of SP {} → PP {} from {} to {}."\
                       .format(switchport.name, patchport.name, patchport.room.short_name, room.short_name),
                       processor, switchport.switch.host.room)

        patchport.room = room

    if switchport.name != switchport_name or patchport.name != patchport_name:
        log_room_event("Changed relation SP {} → PP {} to {} → {} on {}.".format(switchport.name, patchport.name,
                                                                                 switchport_name, patchport_name,
                                                                                 switchport.switch.name),
                       processor, switchport.switch.host.room)

        switchport.name = switchport_name
        patchport.name = patchport_name


@with_transaction
def create_port_relation(switch, switchport_name, patchport_name, room, processor):
    switchport = SwitchPort(name=switchport_name, switch=switch)
    patchport = PatchPort(name=patchport_name, room=room, switch_port=switchport)

    log_room_event("Created relation SP {} → PP {} on {}.".format(switchport.name, patchport.name, switchport.switch.name),
                   processor, switchport.switch.host.room)


@with_transaction
def delete_port_relation(switchport, patchport, processor):
    log_room_event(
        "Deleted relation SP {} → PP {} on {}.".format(switchport.name, patchport.name, switchport.switch.name),
        processor, switchport.switch.host.room)

    session.delete(patchport)
    session.delete(switchport)


@with_transaction
def edit_switch(switch, name, management_ip, room, processor):
    if switch.name != name:
        log_room_event("Changed name of '{}' to '{}'.".format(switch.name, name), processor, switch.host.room)

        switch.name = name

    if switch.host.room != room:
        log_room_event("Moved switch '{}' from {} to {}.".format(switch.name, switch.host.room, room), processor, switch.host.room)

        switch.host.room = room

    if switch.management_ip != management_ip:
        log_room_event("Changed management IP of switch '{}' from {} to {}."
                       .format(switch.name, switch.management_ip, management_ip), processor, switch.host.room)

        switch.management_ip = management_ip


@with_transaction
def create_switch(name, management_ip, room, processor):
    switch = Switch(name=name, management_ip=management_ip, host=Host(room=room, owner=User.q.get(0), name=name))

    log_room_event("Created switch '{}' with management IP {}.".format(switch.name, switch.management_ip),
                   processor, switch.host.room)

    return switch


@with_transaction
def delete_switch(switch, processor):
    log_room_event("Deleted switch {}.".format(switch.name), processor, switch.host.room)

    session.delete(switch)
