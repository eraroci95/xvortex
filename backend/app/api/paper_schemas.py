import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.api.market_schemas import SYMBOL_RE


class AccountIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    starting_cash: Decimal = Field(gt=0, le=1_000_000_000, max_digits=12, decimal_places=2)
    currency: str = Field(default="SEK", pattern=r"^[A-Z]{3}$")

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Name must not be blank.")
        return v


class OrderIn(BaseModel):
    """Market orders only: filled at the latest saved end-of-day close."""
    symbol: str = Field(min_length=1, max_length=16)
    side: Literal["buy", "sell"]
    quantity: Decimal = Field(gt=0, le=1_000_000_000, max_digits=14, decimal_places=4)

    @field_validator("symbol")
    @classmethod
    def _symbol(cls, v: str) -> str:
        v = v.strip().upper()
        if not SYMBOL_RE.match(v):
            raise ValueError("Use letters, digits, dots and dashes only, for example IBM.")
        return v


class PositionOut(BaseModel):
    symbol: str
    quantity: Decimal
    avg_entry_price: Decimal
    cost_basis: Decimal
    last_close: Decimal | None
    price_date: date | None
    market_value: Decimal | None
    unrealized_pnl: Decimal | None
    realized_pnl: Decimal


class TradeOut(BaseModel):
    id: uuid.UUID
    executed_at: datetime
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    amount: Decimal
    fees: Decimal
    realized_pnl: Decimal | None
    simulated: bool = True


class AccountOut(BaseModel):
    id: uuid.UUID
    name: str
    currency: str
    starting_cash: Decimal
    cash_balance: Decimal
    positions: list[PositionOut]
    market_value: Decimal | None  # None when an open position has no saved price
    equity: Decimal | None  # cash plus market value, same condition
    unrealized_pnl: Decimal | None
    realized_pnl: Decimal
    valuation_status: Literal["end_of_day", "partial", "unavailable"]
    trades: list[TradeOut]
    simulated: bool = True


class OrderResult(BaseModel):
    account: AccountOut
    trade: TradeOut
    price_date: date
