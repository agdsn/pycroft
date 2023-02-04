# Copyright (c) 2015 The Pycroft Authors. See the AUTHORS file.
# This file is part of the Pycroft project and licensed under the terms of
# the Apache License, Version 2.0. See the LICENSE file for details.
"""
    pycroft.model.logging
    ~~~~~~~~~~~~~~~~~~~~~

    This module contains the classes LogEntry, UserLogEntry, TrafficVolume.

    :copyright: (c) 2011 by AG DSN.
"""
from __future__ import annotations
import typing as t
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.types import Text

from pycroft.model.base import IntegerIdModel
from pycroft.model.type_aliases import str50, datetime_tz

if t.TYPE_CHECKING:
    # FKeys
    from .user import User
    from .task import Task
    from .facilities import Room

    # Backrefs


class LogEntry(IntegerIdModel):
    discriminator: Mapped[str50] = mapped_column("type")
    __mapper_args__ = {"polymorphic_on": discriminator}

    # variably sized string
    message: Mapped[str] = mapped_column(Text)
    # created
    created_at: Mapped[datetime_tz]

    # many to one from LogEntry to User
    author_id: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
    author: Mapped[User] = relationship("User", back_populates="authored_log_entries")


class TaskLogEntry(LogEntry):
    __mapper_args__ = {"polymorphic_identity": "task_log_entry"}
    id: Mapped[int] = mapped_column(
        ForeignKey(LogEntry.id, ondelete="CASCADE"), primary_key=True
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("task.id", ondelete="CASCADE"), index=True
    )
    task: Mapped[Task] = relationship(back_populates="log_entries")

    # many to one from UserLogEntry to User
    user: Mapped[User] = relationship(
        primaryjoin="TaskLogEntry.task_id == UserTask.id",
        secondary="user_task",
        back_populates="task_log_entries",
        viewonly=True,
    )


class UserLogEntry(LogEntry):
    __mapper_args__ = {"polymorphic_identity": "user_log_entry"}
    id: Mapped[int] = mapped_column(
        ForeignKey(LogEntry.id, ondelete="CASCADE"), primary_key=True
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), index=True
    )
    user: Mapped[User] = relationship(back_populates="log_entries")


class RoomLogEntry(LogEntry):
    __mapper_args__ = {"polymorphic_identity": "room_log_entry"}
    id: Mapped[int] = mapped_column(ForeignKey("log_entry.id"), primary_key=True)

    # many to one from RoomLogEntry to Room
    room_id: Mapped[int] = mapped_column(
        ForeignKey("room.id", ondelete="CASCADE"), index=True
    )
    room: Mapped[Room] = relationship(back_populates="log_entries")
