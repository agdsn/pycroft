# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
pycroft.model.port
~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations

from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import relationship, mapped_column, Mapped

from pycroft.model import ddl
from .base import IntegerIdModel
from .facilities import Room
from .host import SwitchPort

manager = ddl.DDLManager()


class PatchPort(IntegerIdModel):
    """A patch panel port that may or not be connected to a switch"""

    id: Mapped[int] = mapped_column(primary_key=True)
    name = mapped_column(String, nullable=False)

    switch_port_id: Mapped[int | None] = mapped_column(
        ForeignKey(SwitchPort.id, ondelete="SET NULL"), unique=True
    )
    switch_port: Mapped[SwitchPort] = relationship(back_populates="patch_port")

    room_id: Mapped[int] = mapped_column(
        ForeignKey("room.id", ondelete="CASCADE"), index=True
    )
    room: Mapped[Room] = relationship(
        foreign_keys=room_id,
        back_populates="patch_ports",
    )

    switch_room_id: Mapped[int] = mapped_column(ForeignKey("room.id"), index=True)
    switch_room: Mapped[Room] = relationship(foreign_keys=switch_room_id)

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
