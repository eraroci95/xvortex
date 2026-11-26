import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import PRIVATE, client_ip, current_user
from app.api.market import STATUS_FOR
from app.api.paper_schemas import AccountIn, AccountOut, OrderIn, OrderResult, PositionOut, TradeOut
from app.core.config import get_settings
from app.db import get_db
from app.models import PaperAccount, PaperOrder, PaperPosition, PaperTrade, User
from app.services.audit import record_audit
from app.services.market import service as market
from app.services.paper.engine import Position, TradeError, buy, money, sell, value_position

router = APIRouter(prefix="/api/paper", tags=["paper"], dependencies=PRIVATE)

MAX_ACCOUNTS = 5
MAX_PRICE_AGE_DAYS = 7  # an order is refused when the latest saved close is older than this
TRADES_SHOWN = 50
ZERO = Decimal("0.00")


def _owned(db: Session, user: User, account_id: uuid.UUID, lock: bool = False) -> PaperAccount:
    stmt = select(PaperAccount).where(PaperAccount.id == account_id, PaperAccount.user_id == user.id)
    if lock:
        # populate_existing: re-read the row's current values, since the account may have been loaded earlier
        # in this request and another order could have committed since.
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    a = db.scalar(stmt)
    if a is None:
        raise HTTPException(404, "Account not found.")
    return a


def _trade_out(t: PaperTrade) -> TradeOut:
    return TradeOut(
        id=t.id, executed_at=t.executed_at, symbol=t.symbol, side=t.side, quantity=t.quantity, price=t.price,
        amount=money(t.quantity * t.price), fees=t.fees, realized_pnl=t.realized_pnl,
    )


def _account_out(db: Session, a: PaperAccount) -> AccountOut:
    rows = db.scalars(select(PaperPosition).where(PaperPosition.account_id == a.id).order_by(PaperPosition.symbol)).all()
    realized = money(sum((p.realized_pnl for p in rows), ZERO))
    positions, priced_value, priced_cost, unpriced = [], ZERO, ZERO, 0
    for p in rows:
        if p.quantity <= 0:
            continue
        saved = market.saved_close(db, p.symbol)
        pos = Position(p.quantity, p.avg_entry_price, p.realized_pnl)
        if saved is None:
            unpriced += 1
            positions.append(PositionOut(
                symbol=p.symbol, quantity=p.quantity, avg_entry_price=p.avg_entry_price,
                cost_basis=money(p.quantity * p.avg_entry_price), last_close=None, price_date=None,
                market_value=None, unrealized_pnl=None, realized_pnl=p.realized_pnl,
            ))
            continue
        v = value_position(pos, saved[0])
        priced_value += v.market_value
        priced_cost += v.cost_basis
        positions.append(PositionOut(
            symbol=p.symbol, quantity=p.quantity, avg_entry_price=p.avg_entry_price, cost_basis=v.cost_basis,
            last_close=saved[0], price_date=saved[1], market_value=v.market_value, unrealized_pnl=v.unrealized_pnl,
            realized_pnl=p.realized_pnl,
        ))
    open_count = len(positions)
    complete = unpriced == 0
    if open_count == 0:
        status = "end_of_day"
    elif complete:
        status = "end_of_day"
    elif unpriced < open_count:
        status = "partial"
    else:
        status = "unavailable"
    trades = db.scalars(
        select(PaperTrade).where(PaperTrade.account_id == a.id).order_by(PaperTrade.executed_at.desc(), PaperTrade.id).limit(TRADES_SHOWN)
    ).all()
    return AccountOut(
        id=a.id, name=a.name, currency=a.currency, starting_cash=a.starting_cash, cash_balance=a.cash_balance,
        positions=positions,
        market_value=money(priced_value) if complete else None,
        equity=money(a.cash_balance + priced_value) if complete else None,
        unrealized_pnl=money(priced_value - priced_cost) if complete else None,
        realized_pnl=realized, valuation_status=status, trades=[_trade_out(t) for t in trades],
    )


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(user: User = Depends(current_user), db: Session = Depends(get_db)):
    accounts = db.scalars(select(PaperAccount).where(PaperAccount.user_id == user.id).order_by(PaperAccount.created_at, PaperAccount.id)).all()
    return [_account_out(db, a) for a in accounts]


@router.post("/accounts", response_model=AccountOut, status_code=201)
def create_account(body: AccountIn, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if (db.scalar(select(func.count(PaperAccount.id)).where(PaperAccount.user_id == user.id)) or 0) >= MAX_ACCOUNTS:
        raise HTTPException(409, f"You can have at most {MAX_ACCOUNTS} paper accounts.")
    a = PaperAccount(user_id=user.id, name=body.name, currency=body.currency, starting_cash=body.starting_cash, cash_balance=body.starting_cash)
    db.add(a)
    db.flush()
    db.refresh(a)
    record_audit(db, "paper_account_created", user_id=user.id, ip=client_ip(request), entity_type="paper_account", entity_id=str(a.id))
    db.commit()
    return _account_out(db, a)


@router.delete("/accounts/{account_id}", status_code=204)
def delete_account(account_id: uuid.UUID, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
    a = _owned(db, user, account_id, lock=True)
    db.delete(a)
    record_audit(db, "paper_account_deleted", user_id=user.id, ip=client_ip(request), entity_type="paper_account", entity_id=str(account_id))
    db.commit()


@router.post("/accounts/{account_id}/orders", response_model=OrderResult, status_code=201)
def place_order(
    account_id: uuid.UUID, body: OrderIn, request: Request,
    user: User = Depends(current_user), db: Session = Depends(get_db),
):
    """Simulated market order, filled at the latest saved end-of-day close. No real order is ever sent."""
    _owned(db, user, account_id)
    if not market.on_watchlist(db, user.id, body.symbol):
        raise HTTPException(409, "Add this symbol to a watchlist first, so its prices can be loaded.")
    # Price first: this may fetch prices and commit, which would release a row lock taken earlier.
    try:
        daily = market.get_daily(db, get_settings(), body.symbol)
    except market.MarketUnavailable as exc:
        raise HTTPException(STATUS_FOR.get(exc.kind, 502), f"No price for {body.symbol}: {exc}")
    last = daily.bars[-1]
    now = datetime.now(timezone.utc)
    if (now.date() - last.day).days > MAX_PRICE_AGE_DAYS:
        raise HTTPException(409, f"The latest saved close for {body.symbol} is from {last.day.isoformat()}, too old to trade on. Refresh its prices in Market.")

    account = _owned(db, user, account_id, lock=True)
    row = db.scalar(select(PaperPosition).where(PaperPosition.account_id == account.id, PaperPosition.symbol == body.symbol))
    pos = Position(row.quantity, row.avg_entry_price, row.realized_pnl) if row else Position(Decimal(0), Decimal(0), ZERO)
    try:
        fill = (buy if body.side == "buy" else sell)(account.cash_balance, pos, body.quantity, last.close)
    except TradeError as exc:
        raise HTTPException(409, str(exc))

    account.cash_balance = fill.cash
    if row is None:
        row = PaperPosition(account_id=account.id, symbol=body.symbol, quantity=fill.position.quantity,
                            avg_entry_price=fill.position.avg_entry_price, realized_pnl=fill.position.realized_pnl)
        db.add(row)
    else:
        row.quantity, row.avg_entry_price, row.realized_pnl = fill.position.quantity, fill.position.avg_entry_price, fill.position.realized_pnl
    order = PaperOrder(
        account_id=account.id, symbol=body.symbol, side=body.side, order_type="market", quantity=body.quantity,
        status="filled", submitted_at=now, filled_at=now, fill_price=last.close,
    )
    db.add(order)
    db.flush()
    trade = PaperTrade(
        account_id=account.id, order_id=order.id, symbol=body.symbol, side=body.side, quantity=body.quantity,
        price=last.close, fees=ZERO, realized_pnl=fill.realized_pnl, executed_at=now,
    )
    db.add(trade)
    record_audit(
        db, "paper_order_filled", user_id=user.id, ip=client_ip(request), entity_type="paper_account",
        entity_id=str(account.id), details={"symbol": body.symbol, "side": body.side, "quantity": str(body.quantity), "price": str(last.close)},
    )
    db.commit()
    return OrderResult(account=_account_out(db, account), trade=_trade_out(trade), price_date=last.day)
