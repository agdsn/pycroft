"""
pycroft.model.task
~~~~~~~~~~~~~~~~~~
"""
from __future__ import annotations
import builtins
import enum
import operator
import typing as t
from collections.abc import Mapping

from marshmallow import Schema
from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import TypeVar, Generic

from pycroft.model.base import IntegerIdModel
from pycroft.model.types import DateTimeTz
from .task_serialization import UserMoveOutSchema, UserMoveSchema, UserMoveInSchema, TaskParams
from .type_aliases import str50
from ..helpers import utc

from .user import User

if t.TYPE_CHECKING:
    from .logging import TaskLogEntry

class TaskType(enum.Enum):
    USER_MOVE_OUT = enum.auto()
    USER_MOVE_IN = enum.auto()
    USER_MOVE = enum.auto()


class TaskStatus(enum.Enum):
    OPEN = enum.auto()
    EXECUTED = enum.auto()
    FAILED = enum.auto()
    CANCELLED = enum.auto()


TSchema = TypeVar('TSchema')
TParams = TypeVar("TParams", bound=TaskParams)


class Task(IntegerIdModel, Generic[TSchema, TParams]):
    """The task model

    The task model needs to hold three types of data:

    - Metadata (creation, status, …)
    - A type (e.g. USER_MOVE)
    - the `parameters_json` json dict.

    The parameters should actually be accessed via :attr:`parameters`,
    as this already takes care of validation and (de-)serialization.
    The `type` field is essentially only needed for filtering in a query.
    """

    discriminator: Mapped[str50] = mapped_column("task_type")
    __mapper_args__ = {'polymorphic_on': discriminator}

    type: Mapped[TaskType]
    due: Mapped[utc.DateTimeTz] = mapped_column(DateTimeTz)
    parameters_json: Mapped[t.Any] = mapped_column("parameters", JSONB)
    created: Mapped[utc.DateTimeTz] = mapped_column(DateTimeTz)
    creator_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    creator: Mapped[User] = relationship(foreign_keys=[creator_id])
    status: Mapped[TaskStatus] = mapped_column(default=TaskStatus.OPEN)
    errors: Mapped[t.Any | None] = mapped_column(JSONB)

    # backrefs
    log_entries: Mapped[list[TaskLogEntry]] = relationship(
        back_populates="task", viewonly=True
    )
    # /backrefs

    @property
    def schema(self) -> builtins.type[Schema]:
        if not task_type_to_schema[self.type]:
            raise ValueError("cannot find schema for task type")

        return task_type_to_schema[self.type]

    @property
    def parameters(self) -> TParams:
        """(Lazily) deserialized dict corresponding to the parameters.

        The deserialization happens according to what schema is referenced in self.schema.
        """
        parameters_schema = self.schema()

        return parameters_schema.load(self.parameters_json)

    @parameters.setter
    def parameters(self, _parameters):
        parameters_schema = self.schema()

        data = parameters_schema.dump(_parameters)

        self.parameters_json = data

    @property
    def latest_log_entry(self) -> TaskLogEntry | None:
        if not (le := self.log_entries):
            return None
        return max(le, key=operator.attrgetter("created_at"))


class UserTask(Task):
    __mapper_args__ = {'polymorphic_identity': 'user_task'}

    id: Mapped[int] = mapped_column(
        ForeignKey(Task.id, ondelete="CASCADE"), primary_key=True
    )

    user_id: Mapped[int] = mapped_column(ForeignKey(User.id))
    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="tasks")


task_type_to_schema: Mapping[TaskType, type[Schema]] = {
    TaskType.USER_MOVE: UserMoveSchema,
    TaskType.USER_MOVE_IN: UserMoveInSchema,
    TaskType.USER_MOVE_OUT: UserMoveOutSchema
}


