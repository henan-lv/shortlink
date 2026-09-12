"""黑名单 Schema。"""

from marshmallow import Schema, fields, validate


class BlacklistCreateRequest(Schema):
    rule_type = fields.Str(required=True, validate=validate.OneOf(
        ["exact", "domain", "keyword", "regex"]
    ))
    pattern = fields.Str(required=True, validate=validate.Length(min=1, max=512))
    enabled = fields.Bool(load_default=True)


class BlacklistResponse(Schema):
    id = fields.Int()
    rule_type = fields.Str()
    pattern = fields.Str()
    enabled = fields.Bool()
    created_at = fields.DateTime()
