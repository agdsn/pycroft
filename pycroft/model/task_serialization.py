from marshmallow import Schema, fields


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
