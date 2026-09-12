"""黑名单表(PRD 第 7.2 节)。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func

from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class Blacklist(db.Model):
    """恶意链接拦截规则。"""

    __tablename__ = "blacklists"

    RULE_TYPE_EXACT = "exact"
    RULE_TYPE_DOMAIN = "domain"
    RULE_TYPE_KEYWORD = "keyword"
    RULE_TYPE_REGEX = "regex"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    rule_type: Mapped[str] = mapped_column(String(16), nullable=False)
    pattern: Mapped[str] = mapped_column(String(512), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    def to_rule(self):
        """转为 SecurityChecker 使用的 BlacklistRule。"""
        from ..services.security import BlacklistRule

        return BlacklistRule(
            rule_type=self.rule_type, pattern=self.pattern, enabled=self.enabled
        )
