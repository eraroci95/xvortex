import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, JSONType, UUIDPk


class Watchlist(Base):
    __tablename__ = "watchlists"
    __table_args__ = (UniqueConstraint("user_id", "name"),)

    id: Mapped[UUIDPk]
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[CreatedAt]


class WatchlistInstrument(Base):
    __tablename__ = "watchlist_instruments"
    __table_args__ = (UniqueConstraint("watchlist_id", "symbol"),)

    id: Mapped[UUIDPk]
    watchlist_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("watchlists.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(32))
    name: Mapped[str | None] = mapped_column(String(200))
    exchange: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[CreatedAt]


class MarketDataCache(Base):
    """Provider responses with explicit fetch/expiry times so the UI can show data freshness."""

    __tablename__ = "market_data_cache"
    __table_args__ = (Index("ix_market_data_cache_symbol_data_type", "symbol", "data_type"),)

    id: Mapped[UUIDPk]
    cache_key: Mapped[str] = mapped_column(String(255), unique=True)
    provider: Mapped[str] = mapped_column(String(50))
    symbol: Mapped[str] = mapped_column(String(32))
    data_type: Mapped[str] = mapped_column(String(32))
    payload: Mapped[dict] = mapped_column(JSONType)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
