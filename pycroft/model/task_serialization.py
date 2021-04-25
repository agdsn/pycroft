from dataclasses import dataclass
from typing import Optional

from datetime import date
from marshmallow import Schema, fields, post_load


class TaskParams:
    pass


class UserMoveOutSchema(Schema):
    comment = fields.Str()
    end_membership = fields.Bool()

    @post_load
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
    begin_membership = fields.Bool(missing=False)
    host_annex = fields.Bool(missing=False)

    @post_load
    def build(self, data, **kwargs):
        return UserMoveInParams(**data)


@dataclass
class UserMoveInParams(TaskParams):
    room_number: str
    level: int
    building_id: int
    mac: Optional[str] = None
    birthdate: Optional[date] = None
    begin_membership: bool = False
    host_annex: bool = False
