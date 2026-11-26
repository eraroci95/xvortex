"""Assembles the Command Center summary from the user's own rows. Nothing here is estimated:
anything that needs a market price or news feed is reported as unavailable instead."""
from collections import defaultdict
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    Borrower, Loan, LoanPayment, LoanRepaymentSchedule, Notification, PaperAccount, PaperPosition,
    PaperTrade, User, UserSettings, Watchlist, WatchlistInstrument,
)
from app.services.loans.amortization import Installment, money
from app.services.market.service import saved_close
from app.services.loans.portfolio import LoanSnapshot, summarize_loans

ZERO = Decimal("0.00")
RECENT_LIMIT = 10


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def loan_snapshots(db: Session, user_id) -> list[LoanSnapshot]:
    loans = db.scalars(
        select(Loan).where(Loan.user_id == user_id, Loan.status == "active", Loan.archived_at.is_(None))
    ).all()
    if not loans:
        return []
    ids = [loan.id for loan in loans]
    schedule: dict = defaultdict(list)
    rows = db.scalars(
        select(LoanRepaymentSchedule).where(LoanRepaymentSchedule.loan_id.in_(ids))
        .order_by(LoanRepaymentSchedule.loan_id, LoanRepaymentSchedule.installment_no)
    )
    for r in rows:
        schedule[r.loan_id].append(Installment(r.installment_no, r.due_date, r.principal_due, r.interest_due))
    payments: dict = defaultdict(list)
    for p in db.scalars(select(LoanPayment).where(LoanPayment.loan_id.in_(ids)).order_by(LoanPayment.paid_on)):
        payments[p.loan_id].append(p.amount)
    return [LoanSnapshot(l.id, l.currency, l.principal, schedule[l.id], payments[l.id]) for l in loans]


def _paper(db: Session, user_id, currency: str) -> dict[str, Any]:
    """Only accounts in the display currency are added up; amounts in other currencies are never mixed in
    (excluded_accounts says how many were left out). Market value uses saved end-of-day closes only."""
    all_accounts = db.scalars(select(PaperAccount).where(PaperAccount.user_id == user_id)).all()
    accounts = [a for a in all_accounts if a.currency == currency]
    positions = []
    if accounts:
        positions = db.scalars(
            select(PaperPosition).where(PaperPosition.account_id.in_([a.id for a in accounts]))
        ).all()
    open_positions = [p for p in positions if p.quantity > 0]
    invested = sum((p.quantity * p.avg_entry_price for p in open_positions), ZERO)
    market_value: Decimal | None = None
    unrealized: Decimal | None = None
    status = "unavailable"
    if accounts:
        closes = {p.symbol: saved_close(db, p.symbol) for p in open_positions}
        priced = [p for p in open_positions if closes[p.symbol] is not None]
        if not open_positions:
            market_value, unrealized, status = ZERO, ZERO, "end_of_day"
        elif priced:
            market_value = money(sum((p.quantity * closes[p.symbol][0] for p in priced), ZERO))
            unrealized = money(market_value - sum((p.quantity * p.avg_entry_price for p in priced), ZERO))
            status = "end_of_day" if len(priced) == len(open_positions) else "partial"
    return {
        "accounts": len(accounts),
        "excluded_accounts": len(all_accounts) - len(accounts),
        "currency": currency,
        "cash": money(sum((a.cash_balance for a in accounts), ZERO)),
        "starting_cash": money(sum((a.starting_cash for a in accounts), ZERO)),
        "invested_at_cost": money(invested),
        "realized_pnl": money(sum((p.realized_pnl for p in positions), ZERO)),
        "market_value": market_value,
        "unrealized_pnl": unrealized,
        "valuation_status": status,
    }


def _watchlists(db: Session, user_id) -> list[dict[str, Any]]:
    lists = db.scalars(select(Watchlist).where(Watchlist.user_id == user_id).order_by(Watchlist.name)).all()
    if not lists:
        return []
    symbols: dict = defaultdict(list)
    rows = db.scalars(
        select(WatchlistInstrument).where(WatchlistInstrument.watchlist_id.in_([w.id for w in lists]))
        .order_by(WatchlistInstrument.symbol)
    )
    for i in rows:
        symbols[i.watchlist_id].append(i.symbol)
    return [
        {"id": w.id, "name": w.name, "symbol_count": len(symbols[w.id]), "symbols": symbols[w.id][:8]}
        for w in lists
    ]


def _transactions(db: Session, user_id, currency: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    trades = db.scalars(
        select(PaperTrade, PaperAccount.currency).join(PaperAccount, PaperTrade.account_id == PaperAccount.id)
        .where(PaperAccount.user_id == user_id).order_by(PaperTrade.executed_at.desc()).limit(RECENT_LIMIT)
    ).all()
    for t, account_currency in trades:
        verb = "Bought" if t.side == "buy" else "Sold"
        items.append({
            "kind": "paper_trade", "label": f"{verb} {t.quantity.normalize():f} {t.symbol}",
            "amount": money(t.quantity * t.price), "currency": account_currency,
            "occurred_at": _utc(t.executed_at), "simulated": True,
        })
    payments = db.execute(
        select(LoanPayment, Borrower.name, Loan.currency)
        .join(Loan, LoanPayment.loan_id == Loan.id).join(Borrower, Loan.borrower_id == Borrower.id)
        .where(Loan.user_id == user_id)
        .order_by(LoanPayment.paid_on.desc(), LoanPayment.created_at.desc()).limit(RECENT_LIMIT)
    ).all()
    for p, borrower, cur in payments:
        items.append({
            "kind": "loan_payment", "label": f"Payment from {borrower}", "amount": p.amount,
            "currency": cur, "occurred_at": datetime.combine(p.paid_on, time.min, timezone.utc),
            "simulated": False,
        })
    items.sort(key=lambda i: i["occurred_at"], reverse=True)
    return items[:RECENT_LIMIT]


def notification_items(db: Session, user_id, limit: int) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Notification).where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc()).limit(limit)
    ).all()
    return [
        {"id": n.id, "kind": n.kind, "title": n.title, "body": n.body,
         "created_at": _utc(n.created_at), "read": n.read_at is not None}
        for n in rows
    ]


def unread_count(db: Session, user_id) -> int:
    return db.scalar(
        select(func.count()).select_from(Notification)
        .where(Notification.user_id == user_id, Notification.read_at.is_(None))
    ) or 0


def build_summary(db: Session, user: User, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    settings = db.get(UserSettings, user.id)
    currency = settings.currency if settings else "SEK"
    totals = summarize_loans(loan_snapshots(db, user.id), today)
    return {
        "generated_at": datetime.now(timezone.utc),
        "loans": [
            {k: getattr(t, k) for k in (
                "currency", "active_loans", "overdue_loans", "total_lent",
                "outstanding_principal", "remaining_interest", "overdue_amount", "unapplied_payments")}
            for t in totals
        ],
        "paper": _paper(db, user.id, currency),
        "watchlists": _watchlists(db, user.id),
        "market_data_status": "end_of_day" if get_settings().alphavantage_api_key else "unavailable",
        "transactions": _transactions(db, user.id, currency),
        "news": {"status": "unavailable", "items": []},
        "notifications": {"unread": unread_count(db, user.id), "latest": notification_items(db, user.id, 5)},
    }
