from marshmallow import Schema, fields
from sqlalchemy import Column, Enum, Integer, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, backref

from pycroft.helpers import AutoNumber
from pycroft.model.base import IntegerIdModel
from pycroft.model.types import DateTimeTz


class TaskType(AutoNumber):
    USER_MOVE_OUT = ()
    USER_MOVE_IN = ()
    USER_MOVE = ()


class TaskStatus(AutoNumber):
    OPEN = ()
    EXECUTED = ()
    FAILED = ()
    CANCELLED = ()


class Task(IntegerIdModel):
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
    def schema(self):
        if not task_type_to_schema[self.type]:
            raise ValueError("cannot find schema for task type")

        return task_type_to_schema[self.type]

    @hybrid_property
    def parameters(self):
        parameters_schema = self.schema()

        return parameters_schema.load(self.parameters_json)

    @parameters.setter
    def parameters(self, _parameters):
        parameters_schema = self.schema()

        data, errors = parameters_schema.dump(_parameters)

        self.parameters_json = data


class UserTask(Task):
    __mapper_args__ = {'polymorphic_identity': 'user_task'}

    id = Column(Integer, ForeignKey(Task.id, ondelete="CASCADE"),
                primary_key=True)

    user = relationship('User', backref=backref("tasks"))
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)


class UserMoveOutSchema(Schema):
    comment = fields.Str()
    end_membership = fields.Bool()


class UserMoveSchema(Schema):
    room_number = fields.Str()
    level = fields.Int()
    building_id = fields.Int()
    comment = fields.Str()
    end_membership = fields.Bool()


class UserMoveInSchema(Schema):
    room_number = fields.Str()
    level = fields.Int()
    building_id = fields.Int()
    mac = fields.Str(allow_none=True, missing=None)
    birthdate = fields.Date(allow_none=True, missing=None)
    begin_membership = fields.Bool(missing=False)
    host_annex = fields.Bool(missing=False)


task_type_to_schema = {
    TaskType.USER_MOVE: UserMoveSchema,
    TaskType.USER_MOVE_IN: UserMoveInSchema,
    TaskType.USER_MOVE_OUT: UserMoveOutSchema
}


