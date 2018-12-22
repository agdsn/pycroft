# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
from sqlalchemy import Column, String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref

from pycroft.model import ddl
from pycroft.model.base import IntegerIdModel
from pycroft.model.facilities import Room
from pycroft.model.host import SwitchPort

manager = ddl.DDLManager()


class PatchPort(IntegerIdModel):
    """A patch panel port that may or not be connected to a switch"""
    id = Column(Integer, primary_key=True)
    name = Column(String(8), nullable=False)

    switch_port_id = Column(Integer, ForeignKey(SwitchPort.id), unique=True)
    switch_port = relationship(SwitchPort,
                               backref=backref("patch_port", uselist=False))

    room_id = Column(Integer, ForeignKey("room.id"), nullable=False, index=True)
    room = relationship(Room, foreign_keys=room_id, backref=backref("patch_ports"))

    switch_room_id = Column(Integer, ForeignKey("room.id"), nullable=False, index=True)
    switch_room = relationship(Room, foreign_keys=switch_room_id)

    #__table_args__ = (UniqueConstraint("name", "switch_room_id"),)


# Ensure that a connected switch is in the switch_room (patch_port.switch_room_id)
manager.add_function(
    PatchPort.__table__,
    ddl.Function(
        'patch_port_switch_in_switch_room', [],
        'trigger',
        """
        DECLARE
          v_patch_port patch_port;
          v_switch_port_switch_host_room_id integer;
        BEGIN
          v_patch_port := NEW;
        
          IF v_patch_port.switch_port_id IS NOT NULL THEN
              SELECT h.room_id INTO v_switch_port_switch_host_room_id FROM patch_port pp
                  JOIN switch_port sp ON pp.switch_port_id = sp.id
                  JOIN host h ON sp.switch_id = h.id
                  WHERE pp.id = v_patch_port.id;
                  
              IF v_switch_port_switch_host_room_id <> v_patch_port.switch_room_id THEN
                RAISE EXCEPTION 'A patch-port can only be patched to a switch that is located in the switch-room of
                                  the patch-port';
              END IF;
          END IF;
          RETURN NULL;
        END;
        """,
        volatility='stable', strict=True, language='plpgsql'
    )
)

manager.add_constraint_trigger(
    PatchPort.__table__,
    ddl.ConstraintTrigger(
        'patch_port_switch_in_switch_room_trigger',
        PatchPort.__table__,
        ('INSERT', 'UPDATE'),
        'patch_port_switch_in_switch_room()',
        deferrable=True, initially_deferred=True,
    )
)

manager.register()
