import re
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,15}$")


class WatchlistIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank.")
        return v


class InstrumentIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)
    name: str | None = Field(default=None, max_length=200)

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not SYMBOL_RE.match(v):
            raise ValueError("Use letters, digits, dots and dashes only, for example IBM or VOLV-B.ST.")
        return v

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return (v.strip() or None) if v is not None else None


class InstrumentOut(BaseModel):
    symbol: str
    name: str | None
    last_close: Decimal | None  # from saved prices only; None until prices have been fetched
    change_pct: Decimal | None  # last close against the one before it
    as_of: date | None  # trading day of last_close
    fetched_at: datetime | None


class WatchlistOut(BaseModel):
    id: str
    name: str
    instruments: list[InstrumentOut]


class BarOut(BaseModel):
    date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class DailyOut(BaseModel):
    symbol: str
    bars: list[BarOut]
    sma20: list[Decimal | None]
    sma50: list[Decimal | None]
    rsi14: list[Decimal | None]
    fetched_at: datetime
    expires_at: datetime
    stale: bool
    warning: str | None
    source: str = "Alpha Vantage"
    note: str = "End-of-day prices, not live quotes. Indicators are calculated here from these closes."


class MarketStatus(BaseModel):
    configured: bool
    budget_used: int
    budget_limit: int
