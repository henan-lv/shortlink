"""访问控制规则表(风控)。

一条规则 = 「对某个访问者维度的匹配条件」+「命中动作」。

维度 rule_type:
  - ip       精确 IP
  - ip_cidr  CIDR 网段(如 10.0.0.0/8)
  - ua       User-Agent 子串(忽略大小写)
  - referer  Referer 子串(忽略大小写)

模式 mode:
  - block  黑名单:命中即按 action 处置
  - allow  白名单:该短码只要存在 allow 规则,未命中的访问一律拒绝

动作 action(仅对 mode=block 生效):
  - block    直接拒绝(跳转返回 404)
  - observe  只计数放行(用于先观察后拦截)

作用范围 scope:
  - short_code  仅对某条短链生效(生成页高级设置 / 统计页对单链一键拦截)
  - global      对该用户名下所有短链生效(统计页全局封禁某 IP)

来源 source:
  - advanced  生成页「高级设置」写入
  - manual    统计页「一键拦截」写入
  - auto      预留:自动风控触发

MySQL 5.7 约束:时间统一 DATETIME(naive UTC),状态用 VARCHAR 便于扩展。
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class AccessRuleType:
    IP = "ip"
    IP_CIDR = "ip_cidr"
    UA = "ua"
    REFERER = "referer"

    ALL = (IP, IP_CIDR, UA, REFERER)


class AccessRuleMode:
    BLOCK = "block"
    ALLOW = "allow"

    ALL = (BLOCK, ALLOW)


class AccessRuleAction:
    BLOCK = "block"
    OBSERVE = "observe"

    ALL = (BLOCK, OBSERVE)


class AccessRuleScope:
    SHORT_CODE = "short_code"
    GLOBAL = "global"

    ALL = (SHORT_CODE, GLOBAL)


class AccessRuleSource:
    ADVANCED = "advanced"
    MANUAL = "manual"
    AUTO = "auto"

    ALL = (ADVANCED, MANUAL, AUTO)


class AccessRule(db.Model):
    """访问控制规则。"""

    __tablename__ = "access_rules"

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"),
        primary_key=True,
        autoincrement=True,
    )
    # 规则归属用户:global 规则只对该用户名下的短链生效,避免跨租户误伤
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    rule_type: Mapped[str] = mapped_column(String(16), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    mode: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AccessRuleMode.BLOCK
    )
    action: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AccessRuleAction.BLOCK
    )

    scope: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AccessRuleScope.SHORT_CODE
    )
    # scope=short_code 时必填;scope=global 时为 NULL
    short_code: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AccessRuleSource.MANUAL
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # 过期时间:为空表示永久;临时封禁应设置(如 24h)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("idx_access_rules_code_enabled", "short_code", "enabled"),
        Index("idx_access_rules_scope_enabled", "scope", "enabled"),
        Index("idx_access_rules_expire", "expire_at"),
    )

    def is_expired(self) -> bool:
        if self.expire_at is None:
            return False
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        exp = (
            self.expire_at
            if self.expire_at.tzinfo is None
            else self.expire_at.astimezone(timezone.utc).replace(tzinfo=None)
        )
        return exp <= now

    def is_active(self) -> bool:
        return bool(self.enabled) and not self.is_expired()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_type": self.rule_type,
            "value": self.value,
            "mode": self.mode,
            "action": self.action,
            "scope": self.scope,
            "short_code": self.short_code,
            "reason": self.reason,
            "source": self.source,
            "enabled": bool(self.enabled),
            "expire_at": self.expire_at.isoformat() if self.expire_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
