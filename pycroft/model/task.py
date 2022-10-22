"""
pycroft.model.task
~~~~~~~~~~~~~~~~~~
"""
import builtins
import enum
import operator
from collections.abc import Mapping

from marshmallow import Schema
from sqlalchemy import Column, Enum, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref
from typing import TypeVar, Generic

from pycroft.model.base import IntegerIdModel
from pycroft.model.types import DateTimeTz
from .task_serialization import UserMoveOutSchema, UserMoveSchema, UserMoveInSchema, TaskParams


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
    discriminator = Column('task_type', String(50))
    __mapper_args__ = {'polymorphic_on': discriminator}

    type = Column(Enum(TaskType), nullable=False)
    due = Column(DateTimeTz, nullable=False)
    parameters_json = Column('parameters', JSONB, nullable=False)
    created = Column(DateTimeTz, nullable=False)
    creator = relationship('User')
    creator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    status = Column(Enum(TaskStatus), nullable=False, default=TaskStatus.OPEN)
    errors = Column(JSONB, nullable=True)

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
    def latest_log_entry(self) -> "TaskLogEntry | None":
        if not (le := self.log_entries):
            return None
        return max(le, key=operator.attrgetter("created_at"))


class UserTask(Task):
    __mapper_args__ = {'polymorphic_identity': 'user_task'}

    id = Column(Integer, ForeignKey(Task.id, ondelete="CASCADE"),
                primary_key=True)

    user = relationship('User', backref=backref("tasks", viewonly=True))
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)


task_type_to_schema: Mapping[TaskType, type[Schema]] = {
    TaskType.USER_MOVE: UserMoveSchema,
    TaskType.USER_MOVE_IN: UserMoveInSchema,
    TaskType.USER_MOVE_OUT: UserMoveOutSchema
}


