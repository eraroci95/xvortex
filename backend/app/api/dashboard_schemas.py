import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LoanTotalsOut(BaseModel):
    currency: str
    active_loans: int
    overdue_loans: int
    total_lent: Decimal
    outstanding_principal: Decimal
    remaining_interest: Decimal
    overdue_amount: Decimal
    unapplied_payments: Decimal


class PaperSummaryOut(BaseModel):
    accounts: int
    currency: str
    cash: Decimal
    starting_cash: Decimal
    invested_at_cost: Decimal
    realized_pnl: Decimal
    market_value: Decimal | None = None
    unrealized_pnl: Decimal | None = None
    valuation_status: str


class WatchlistBrief(BaseModel):
    id: uuid.UUID
    name: str
    symbol_count: int
    symbols: list[str]


class TransactionOut(BaseModel):
    kind: str
    label: str
    amount: Decimal
    currency: str | None
    occurred_at: datetime
    simulated: bool


class NotificationOut(BaseModel):
    id: uuid.UUID
    kind: str
    title: str
    body: str | None
    created_at: datetime
    read: bool


class NotificationBlock(BaseModel):
    unread: int
    latest: list[NotificationOut]


class NewsBlock(BaseModel):
    status: str
    items: list[dict] = []


class DashboardSummary(BaseModel):
    generated_at: datetime
    loans: list[LoanTotalsOut]
    paper: PaperSummaryOut
    watchlists: list[WatchlistBrief]
    market_data_status: str
    transactions: list[TransactionOut]
    news: NewsBlock
    notifications: NotificationBlock


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationOut]


class WidgetPref(BaseModel):
    id: str = Field(max_length=32)
    visible: bool


class LayoutIO(BaseModel):
    widgets: list[WidgetPref] = Field(max_length=20)
