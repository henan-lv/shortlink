"""用户表(PRD 第 7.2 节)。"""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, func

from sqlalchemy.orm import Mapped, mapped_column

from ..extensions import db


class User(db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
