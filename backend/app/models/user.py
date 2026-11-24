import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, JSONType, UUIDPk


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUIDPk]
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    is_admin: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[CreatedAt]
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    theme: Mapped[str] = mapped_column(String(10), server_default="dark")
    currency: Mapped[str] = mapped_column(String(3), server_default="SEK")
    dashboard_layout: Mapped[dict | None] = mapped_column(JSONType)
    loan_amortization_method: Mapped[str] = mapped_column(String(20), server_default="annuity")
    ai_enabled: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    ai_external_sharing_consent: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    paper_starting_cash: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default="100000")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserSession(Base):
    """Server-side session. `id` is the SHA-256 hex digest of the cookie token (never the token)."""

    __tablename__ = "sessions"
    __table_args__ = (
        Index("ix_sessions_user_id", "user_id"),
        Index("ix_sessions_expires_at", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[CreatedAt]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
