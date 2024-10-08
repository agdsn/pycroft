#  Copyright (c) 2022. The Pycroft Authors. See the AUTHORS file.
#  This file is part of the Pycroft project and licensed under the terms of
#  the Apache License, Version 2.0. See the LICENSE file for details
from netaddr import IPAddress

from pycroft.lib import infrastructure as infra
from tests import factories


def test_create_switch(session, switch_room, processor):
    switch = infra.create_switch(
        session,
        name="Switch",
        management_ip=IPAddress("10.10.10.1"),
        room=switch_room,
        processor=processor,
    )
    session.flush()
    assert switch.host.name == "Switch"
    assert switch_room.latest_log_entry


def test_edit_switch_name(session, switch, processor):
    infra.edit_switch(
        session,
        switch=switch,
        name="New Name",
        management_ip="10.10.10.1",
        room=switch.host.room,
        processor=processor,
    )
    session.flush()
    assert switch.host.name == "New Name"


def test_edit_switch_ip(session, switch, processor):
    infra.edit_switch(
        session,
        switch=switch,
        name=switch.host.name,
        management_ip="10.10.10.2",
        room=switch.host.room,
        processor=processor,
    )
    session.flush()
    session.refresh(switch)
    assert switch.management_ip == IPAddress("10.10.10.2")


def test_edit_switch_room(session, switch, processor):
    new_room = factories.RoomFactory(inhabitable=False)
    infra.edit_switch(
        session,
        switch=switch,
        name=switch.host.name,
        management_ip="10.10.10.1",
        room=new_room,
        processor=processor,
    )
    session.flush()
    assert switch.host.room == new_room


def test_delete_switch(session, switch, processor):
    room = switch.host.room
    infra.delete_switch(session, switch, processor=processor)
    session.flush()
    assert room.hosts == []
