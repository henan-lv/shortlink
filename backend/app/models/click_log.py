"""点击日志表(PRD 第 7.2 节)。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, func

from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class ClickLog(db.Model):
    __tablename__ = "click_logs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(String(16), nullable=False)
    ip: Mapped[str] = mapped_column(String(64), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    referer: Mapped[str | None] = mapped_column(String(512), nullable=True)
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    __table_args__ = (
        # 趋势统计 / UV 计算
        Index("idx_click_logs_code_time", "short_code", "clicked_at"),
        Index("idx_click_logs_code_ip", "short_code", "ip"),
    )
