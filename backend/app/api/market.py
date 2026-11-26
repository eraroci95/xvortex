import uuid
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import PRIVATE, current_user
from app.api.market_schemas import (
    BarOut, DailyOut, InstrumentIn, InstrumentOut, MarketStatus, SYMBOL_RE, WatchlistIn, WatchlistOut,
)
from app.core.config import get_settings
from app.db import get_db
from app.models import MarketDataCache, User, Watchlist, WatchlistInstrument
from app.services.market import service
from app.services.market.indicators import rsi, sma

router = APIRouter(prefix="/api/market", tags=["market"], dependencies=PRIVATE)

MAX_WATCHLISTS = 20
MAX_INSTRUMENTS = 30
STATUS_FOR = {"not_configured": 503, "budget": 429, "rate_limit": 429, "invalid_symbol": 404, "auth": 502, "unavailable": 502}


def _owned(db: Session, user: User, watchlist_id: uuid.UUID) -> Watchlist:
    w = db.scalar(select(Watchlist).where(Watchlist.id == watchlist_id, Watchlist.user_id == user.id))
    if w is None:
        raise HTTPException(404, "Watchlist not found.")
    return w


def _out(db: Session, lists: list[Watchlist]) -> list[WatchlistOut]:
    """Built from saved prices only: listing watchlists never spends a provider request."""
    ids = [w.id for w in lists]
    rows = db.scalars(
        select(WatchlistInstrument).where(WatchlistInstrument.watchlist_id.in_(ids)).order_by(WatchlistInstrument.symbol)
    ).all() if ids else []
    symbols = {r.symbol for r in rows}
    caches = {}
    if symbols:
        for c in db.scalars(select(MarketDataCache).where(MarketDataCache.cache_key.in_([service.cache_key(s) for s in symbols]))):
            caches[c.symbol] = c
    quotes = {}
    for sym, c in caches.items():
        bars = service.decode_bars(c.payload)
        if not bars:
            continue
        last = bars[-1]
        change = None
        if len(bars) > 1 and bars[-2].close != 0:
            change = ((last.close - bars[-2].close) / bars[-2].close * 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        quotes[sym] = (last.close, change, last.day, service._utc(c.fetched_at))
    by_list: dict = {w.id: [] for w in lists}
    for r in rows:
        q = quotes.get(r.symbol)
        by_list[r.watchlist_id].append(InstrumentOut(
            symbol=r.symbol, name=r.name, last_close=q[0] if q else None, change_pct=q[1] if q else None,
            as_of=q[2] if q else None, fetched_at=q[3] if q else None,
        ))
    return [WatchlistOut(id=str(w.id), name=w.name, instruments=by_list[w.id]) for w in lists]


@router.get("/status", response_model=MarketStatus)
def status(db: Session = Depends(get_db)):
    s = get_settings()
    return MarketStatus(
        configured=bool(s.alphavantage_api_key), budget_used=service.budget_used(db, datetime.now(timezone.utc)),
        budget_limit=s.alphavantage_daily_limit,
    )


@router.get("/watchlists", response_model=list[WatchlistOut])
def list_watchlists(user: User = Depends(current_user), db: Session = Depends(get_db)):
    lists = list(db.scalars(select(Watchlist).where(Watchlist.user_id == user.id).order_by(func.lower(Watchlist.name))))
    return _out(db, lists)


@router.post("/watchlists", response_model=WatchlistOut, status_code=201)
def create_watchlist(body: WatchlistIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if (db.scalar(select(func.count(Watchlist.id)).where(Watchlist.user_id == user.id)) or 0) >= MAX_WATCHLISTS:
        raise HTTPException(409, f"You can have at most {MAX_WATCHLISTS} watchlists.")
    w = Watchlist(user_id=user.id, name=body.name)
    db.add(w)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You already have a watchlist with that name.")
    return _out(db, [w])[0]


@router.patch("/watchlists/{watchlist_id}", response_model=WatchlistOut)
def rename_watchlist(watchlist_id: uuid.UUID, body: WatchlistIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = _owned(db, user, watchlist_id)
    w.name = body.name
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "You already have a watchlist with that name.")
    return _out(db, [w])[0]


@router.delete("/watchlists/{watchlist_id}", status_code=204)
def delete_watchlist(watchlist_id: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.delete(_owned(db, user, watchlist_id))
    db.commit()


@router.post("/watchlists/{watchlist_id}/instruments", response_model=WatchlistOut, status_code=201)
def add_instrument(watchlist_id: uuid.UUID, body: InstrumentIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = _owned(db, user, watchlist_id)
    if (db.scalar(select(func.count(WatchlistInstrument.id)).where(WatchlistInstrument.watchlist_id == w.id)) or 0) >= MAX_INSTRUMENTS:
        raise HTTPException(409, f"A watchlist can hold at most {MAX_INSTRUMENTS} symbols.")
    db.add(WatchlistInstrument(watchlist_id=w.id, symbol=body.symbol, name=body.name))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, "That symbol is already in this watchlist.")
    return _out(db, [w])[0]


@router.delete("/watchlists/{watchlist_id}/instruments/{symbol}", response_model=WatchlistOut)
def remove_instrument(watchlist_id: uuid.UUID, symbol: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    w = _owned(db, user, watchlist_id)
    inst = db.scalar(select(WatchlistInstrument).where(WatchlistInstrument.watchlist_id == w.id, WatchlistInstrument.symbol == symbol.upper()))
    if inst is None:
        raise HTTPException(404, "Symbol not found in this watchlist.")
    db.delete(inst)
    db.commit()
    return _out(db, [w])[0]


@router.get("/symbols/{symbol}/daily", response_model=DailyOut)
def daily(symbol: str, refresh: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Only symbols on one of the caller's watchlists can be loaded, so the shared request budget is not
    spent on arbitrary lookups."""
    symbol = symbol.strip().upper()
    if not SYMBOL_RE.match(symbol):
        raise HTTPException(422, "Invalid symbol.")
    if not service.on_watchlist(db, user.id, symbol):
        raise HTTPException(404, "Add this symbol to a watchlist first.")
    try:
        d = service.get_daily(db, get_settings(), symbol, force=refresh)
    except service.MarketUnavailable as exc:
        raise HTTPException(STATUS_FOR.get(exc.kind, 502), str(exc))
    closes = [b.close for b in d.bars]
    return DailyOut(
        symbol=symbol,
        bars=[BarOut(date=b.day, open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume) for b in d.bars],
        sma20=sma(closes, 20), sma50=sma(closes, 50), rsi14=rsi(closes, 14),
        fetched_at=d.fetched_at, expires_at=d.expires_at, stale=d.stale, warning=d.warning,
    )
