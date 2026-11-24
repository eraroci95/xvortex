import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, ForeignKey, Index, Numeric, String,
    UniqueConstraint, Uuid, func, text,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, Money, Price, Quantity, UUIDPk


class PaperAccount(Base):
    __tablename__ = "paper_accounts"
    __table_args__ = (
        CheckConstraint("cash_balance >= 0", name="cash_non_negative"),
        Index("ix_paper_accounts_user_id", "user_id"),
    )

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    starting_cash: Mapped[Money]
    cash_balance: Mapped[Money]
    created_at: Mapped[CreatedAt]


class PaperOrder(Base):
    __tablename__ = "paper_orders"
    __table_args__ = (
        CheckConstraint("side IN ('buy','sell')", name="side_valid"),
        CheckConstraint("order_type IN ('market','limit')", name="type_valid"),
        CheckConstraint("quantity > 0", name="quantity_positive"),
        CheckConstraint("is_simulated IS TRUE", name="always_simulated"),
        Index("ix_paper_orders_account_id_submitted_at", "account_id", "submitted_at"),
    )

    id: Mapped[UUIDPk]
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("paper_accounts.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(4))
    order_type: Mapped[str] = mapped_column(String(8))
    quantity: Mapped[Quantity]
    limit_price: Mapped[Price | None]
    status: Mapped[str] = mapped_column(String(12), server_default="pending")
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    fill_price: Mapped[Price | None]
    is_simulated: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))


class PaperPosition(Base):
    __tablename__ = "paper_positions"
    __table_args__ = (
        UniqueConstraint("account_id", "symbol"),
        CheckConstraint("quantity >= 0", name="quantity_non_negative"),
    )

    id: Mapped[UUIDPk]
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("paper_accounts.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(32))
    quantity: Mapped[Quantity]
    avg_entry_price: Mapped[Price]
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default="0")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PaperTrade(Base):
    __tablename__ = "paper_trades"
    __table_args__ = (
        CheckConstraint("is_simulated IS TRUE", name="always_simulated"),
        Index("ix_paper_trades_account_id_executed_at", "account_id", "executed_at"),
    )

    id: Mapped[UUIDPk]
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("paper_accounts.id", ondelete="CASCADE"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("paper_orders.id", ondelete="SET NULL"))
    symbol: Mapped[str] = mapped_column(String(32))
    side: Mapped[str] = mapped_column(String(4))
    quantity: Mapped[Quantity]
    price: Mapped[Price]
    fees: Mapped[Decimal] = mapped_column(Numeric(18, 2), server_default="0")
    realized_pnl: Mapped[Money | None]
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_simulated: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
