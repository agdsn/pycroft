from dataclasses import dataclass
from typing import Optional

from datetime import date
from marshmallow import Schema, fields, post_load


class UserMoveOutSchema(Schema):
    comment = fields.Str()
    end_membership = fields.Bool()

    @post_load
    def build(self, data, **kwargs):
        return UserMoveOutParams(**data)


@dataclass
class UserMoveOutParams:
    comment: str
    end_membership: bool


class UserMoveSchema(Schema):
    room_number = fields.Str()
    level = fields.Int()
    building_id = fields.Int()
    comment = fields.Str()
    end_membership = fields.Bool()

    @post_load
    def build(self, data, **kwargs):
        return UserMoveParams(**data)


@dataclass
class UserMoveParams:
    room_number: str
    level: int
    building_id: int
    comment: str
    end_membership: bool


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
class UserMoveInParams:
    room_number: str
    level: int
    building_id: int
    mac: Optional[str]
    birthdate: Optional[date]
    begin_membership: bool
    host_annex: bool
