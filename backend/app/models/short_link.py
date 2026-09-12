"""短链表(PRD 第 7.2 节)。

MySQL 5.7 约束:
- utf8mb4 / InnoDB
- 长链用 url_hash 列做唯一索引(规避 767 字节前缀限制)
- 密码可空,加盐哈希存储
- 状态字段用 VARCHAR 而非 ENUM(便于扩展)
"""

from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class ShortLinkStatus:
    ENABLED = "enabled"   # 启用
    DISABLED = "disabled" # 停用
    MALICIOUS = "malicious"  # 恶意


class ShortLink(db.Model):
    __tablename__ = "short_links"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)

    short_code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    long_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # 自定义域名:None 表示使用 BASE_DOMAIN。长链+域名+渠道 联合去重(同输入 -> 同短码)
    domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 渠道参数:None 表示无渠道。如微信/公众号/APP 等不同推广渠道
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)

    visit_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # PV
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=ShortLinkStatus.ENABLED
    )
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    click_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_visit_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    effective_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expire_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_short_links_status_deleted", "status", "is_deleted"),
        Index("idx_short_links_expire", "expire_at"),
        Index("idx_short_links_effective", "effective_at"),
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

    def is_not_effective(self) -> bool:
        """未到生效时间(返回 True 表示还没生效)。"""
        if self.effective_at is None:
            return False
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        eff = (
            self.effective_at
            if self.effective_at.tzinfo is None
            else self.effective_at.astimezone(timezone.utc).replace(tzinfo=None)
        )
        return eff > now

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "short_code": self.short_code,
            "long_url": self.long_url,
            "full_short_url": f"{self.short_code}",  # 由调用方拼 BASE_DOMAIN
            "pv": self.visit_count,
            "uv": 0,  # 由 stats service 计算
            "status": self.status,
            "has_password": bool(self.password_hash),
            "is_deleted": self.is_deleted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "effective_at": self.effective_at.isoformat() if self.effective_at else None,
            "expire_at": self.expire_at.isoformat() if self.expire_at else None,
            "last_visit_at": self.last_visit_at.isoformat() if self.last_visit_at else None,
            "domain": self.domain,
            "channel": self.channel,
        }
