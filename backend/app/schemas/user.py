"""用户/鉴权相关 Schema。"""

from marshmallow import Schema, fields, validate


class RegisterRequest(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=64))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=64))


class LoginRequest(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class UserResponse(Schema):
    id = fields.Int()
    username = fields.Str()
    api_key = fields.Str(allow_none=True)
    is_admin = fields.Bool()
    is_active = fields.Bool()
    created_at = fields.DateTime()


class AdminCreateUserRequest(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=64))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=64))
    is_admin = fields.Bool(load_default=False)


class AdminUpdateUserRequest(Schema):
    is_active = fields.Bool()
    is_admin = fields.Bool()
    password = fields.Str(validate=validate.Length(min=6, max=64))
