"""
pycroft.model.task_serialization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
"""
from dataclasses import dataclass
from datetime import date

import wrapt
from marshmallow import Schema, fields, post_load, ValidationError


@dataclass
class TaskParams:
    pass


@wrapt.decorator
def handle_validation_error[T](wrapped: T, instance, args, kwargs) -> T:
    try:
        return wrapped(*args, **kwargs)
    except TypeError as e:
        raise ValidationError(f"TypeError in post_load: {e}") from e
    except ValueError as e:
        raise ValidationError(f"ValueError in post_load: {e}") from e


class UserMoveOutSchema(Schema):
    comment = fields.Str()
    end_membership = fields.Bool()

    @post_load
    @handle_validation_error
    def build(self, data, **kwargs):
        return UserMoveOutParams(**data)


@dataclass
class UserMoveOutParams(TaskParams):
    comment: str
    end_membership: bool


class UserMoveSchema(Schema):
    room_number = fields.Str()
    level = fields.Int()
    building_id = fields.Int()
    comment = fields.Str(allow_none=True, load_default=None)

    @post_load
    @handle_validation_error
    def build(self, data, **kwargs):
        return UserMoveParams(**data)


@dataclass
class UserMoveParams(TaskParams):
    room_number: str
    level: int
    building_id: int
    comment: str | None = None


class UserMoveInSchema(Schema):
    room_number = fields.Str()
    level = fields.Int()
    building_id = fields.Int()
    mac = fields.Str(allow_none=True, load_default=None)
    birthdate = fields.Date(allow_none=True, load_default=None)
    begin_membership = fields.Bool(load_default=True)
    host_annex = fields.Bool(load_default=False)

    @post_load
    @handle_validation_error
    def build(self, data, **kwargs):
        return UserMoveInParams(**data)


@dataclass
class UserMoveInParams(TaskParams):
    room_number: str
    level: int
    building_id: int
    mac: str | None = None
    birthdate: date | None = None
    begin_membership: bool = True
    host_annex: bool = False
