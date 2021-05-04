from dataclasses import dataclass
from typing import Optional, Callable, TypeVar

from datetime import date

import wrapt
from marshmallow import Schema, fields, post_load, ValidationError


@dataclass
class TaskParams:
    pass


T = TypeVar('T')
handle_validation_error: Callable[[T], T]

@wrapt.decorator
def handle_validation_error(wrapped, instance, args, kwargs):
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
    comment = fields.Str(allow_none=True, missing=None)

    @post_load
    @handle_validation_error
    def build(self, data, **kwargs):
        return UserMoveParams(**data)


@dataclass
class UserMoveParams(TaskParams):
    room_number: str
    level: int
    building_id: int
    comment: Optional[str] = None


class UserMoveInSchema(Schema):
    room_number = fields.Str()
    level = fields.Int()
    building_id = fields.Int()
    mac = fields.Str(allow_none=True, missing=None)
    birthdate = fields.Date(allow_none=True, missing=None)
    begin_membership = fields.Bool(missing=True)
    host_annex = fields.Bool(missing=False)

    @post_load
    @handle_validation_error
    def build(self, data, **kwargs):
        return UserMoveInParams(**data)


@dataclass
class UserMoveInParams(TaskParams):
    room_number: str
    level: int
    building_id: int
    mac: Optional[str] = None
    birthdate: Optional[date] = None
    begin_membership: bool = True
    host_annex: bool = False
