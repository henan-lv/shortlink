"""短链相关请求/响应 Schema(Marshmallow)。"""

from marshmallow import Schema, fields, validate


class CreateShortLinkRequest(Schema):
    """生成短链请求体。"""
    long_url = fields.Str(required=True, validate=validate.Length(min=1, max=2048))
    password = fields.Str(load_default=None, validate=validate.Length(min=6, max=8))
    effective_at = fields.DateTime(load_default=None)  # ISO 8601, 可选, 默认立即生效
    expire_at = fields.DateTime(load_default=None)        # ISO 8601
    click_limit = fields.Int(load_default=None, validate=validate.Range(min=1))
    # 自定义域名(如 s.example.com),不填则使用 BASE_DOMAIN
    domain = fields.Str(load_default=None, validate=validate.Length(max=128))
    # 渠道参数(如 wechat/twitter/app),不填则为无渠道
    channel = fields.Str(load_default=None, validate=validate.Length(max=32))
    # 高级设置:结构化风控配置,由 services/access_control.parse_advanced 解析。
    # 结构:
    #   {
    #     "access_control": {
    #       "block_ips":     ["1.2.3.4", "10.0.0.0/8"],   # 黑名单 IP / CIDR
    #       "block_ua":      ["bot", "spider"],           # 黑名单 UA 关键词
    #       "block_referer": ["spam.example"],            # 黑名单 Referer 关键词
    #       "allow_ips":     ["203.0.113.0/24"],          # 白名单 IP / CIDR(配了则未命中即拒)
    #       "action":        "block"                       # block | observe
    #     }
    #   }
    # 留空(None)表示不配置风控,不影响已有规则。
    advanced = fields.Dict(load_default=None)


class UpdateShortLinkRequest(Schema):
    """修改短链状态请求体(启停)。"""
    status = fields.Str(required=True, validate=validate.OneOf(["enabled", "disabled"]))


class ShortLinkResponse(Schema):
    """短链响应。"""
    id = fields.Int()
    short_code = fields.Str()
    long_url = fields.Str()
    full_short_url = fields.Str()
    status = fields.Str()
    has_password = fields.Bool()
    is_deleted = fields.Bool()
    deleted_at = fields.DateTime(allow_none=True)
    pv = fields.Int()
    uv = fields.Int()
    click_limit = fields.Int(allow_none=True)
    created_at = fields.DateTime()
    effective_at = fields.DateTime(allow_none=True)
    expire_at = fields.DateTime(allow_none=True)
    last_visit_at = fields.DateTime(allow_none=True)


class ShortLinkListQuery(Schema):
    """我的链接列表查询参数。"""
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    page_size = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    include_deleted = fields.Bool(load_default=False)
    # 回收站视图:只看已软删记录。优先于 include_deleted
    only_deleted = fields.Bool(load_default=False)
    status = fields.Str(load_default=None, validate=validate.OneOf(
        ["enabled", "disabled", "malicious"]
    ))
    # 关键词:模糊匹配 短码 或 长链
    keyword = fields.Str(load_default=None, validate=validate.Length(max=128))
    # 渠道 / 自定义域名:精确匹配
    channel = fields.Str(load_default=None, validate=validate.Length(max=32))
    domain = fields.Str(load_default=None, validate=validate.Length(max=128))
    # 排序白名单,非法值直接 400 而不是静默兜底
    sort = fields.Str(load_default="created_desc", validate=validate.OneOf([
        "created_desc", "created_asc", "pv_desc", "last_visit_desc",
    ]))


class ShortLinkListResponse(Schema):
    total = fields.Int()
    page = fields.Int()
    page_size = fields.Int()
    items = fields.List(fields.Nested(ShortLinkResponse))


class VerifyPasswordRequest(Schema):
    password = fields.Str(required=True, validate=validate.Length(min=6, max=8))
